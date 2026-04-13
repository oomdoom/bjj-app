# bjj-app

FastAPI service for listing BJJ techniques, containerised and deployed to AWS EKS. DB credentials are fetched at runtime from AWS Secrets Manager via IRSA — nothing sensitive lives in the image or K8s Secrets.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness/readiness check — returns `{"status": "ok"}` |
| `GET` | `/techniques` | List all techniques (name, position) |
| `POST` | `/init` | Create the `techniques` table and seed three rows |
| `GET` | `/metrics` | Metrics stub |

## Stack

- **Runtime**: Python 3.11, FastAPI, Uvicorn (port 80)
- **Database**: PostgreSQL via `psycopg2` (RDS, private subnet)
- **Secrets**: AWS Secrets Manager → `bjj-db-secret-v2` (read via `boto3`)
- **Container**: `python:3.11` base image
- **Orchestration**: Kubernetes on EKS, namespace `bjj-app`
- **Ingress**: AWS ALB (internet-facing) via the AWS Load Balancer Controller

## Repository layout

```
bjj-app/
├── .github/workflows/
│   ├── build.yaml     # build + push to ECR on merge to main
│   └── deploy.yaml    # kubectl apply to EKS after a successful build
├── app/
│   ├── main.py        # FastAPI application
│   ├── db.py
│   ├── Dockerfile
│   └── requirements.txt
└── k8s/
    ├── namespace.yaml
    ├── deployment.yaml      # 1 replica, readiness + liveness probes on /health
    ├── service.yaml
    ├── ingress.yaml         # ALB internet-facing
    ├── service-account.yaml # IRSA annotation linking pod to AWS IAM role
    ├── secret.yaml
    └── aws-auth.yaml
```

## CI/CD

### Build (`build.yaml`)
Triggered on push to `main`:
1. Authenticate to ECR
2. Build `./app/Dockerfile`
3. Push image tagged with the commit SHA and `latest`

### Deploy (`deploy.yaml`)
Triggered automatically after a successful Build run (also supports `workflow_dispatch`):
1. Authenticate to ECR and update kubeconfig for the EKS cluster
2. Substitute `YOUR_IMAGE` and `YOUR_RDS_ENDPOINT` placeholders in `k8s/deployment.yaml`
3. `kubectl apply -f k8s/`

## Required GitHub secrets

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | IAM credentials with ECR push + EKS access |
| `AWS_SECRET_ACCESS_KEY` | |
| `ECR_REPO` | ECR repository name (e.g. `bjj-api`) |
| `EKS_CLUSTER_NAME` | Name of the EKS cluster (e.g. `bjj-eks`) |
| `RDS_ENDPOINT` | RDS instance hostname injected into the deployment |

## Environment variables (container)

| Variable | Source | Description |
|----------|--------|-------------|
| `SECRET_NAME` | K8s manifest | Secrets Manager secret name (`bjj-db-secret-v2`) |
| `AWS_REGION` | K8s manifest | AWS region (`us-east-1`) |
| `DB_HOST` | Injected by deploy workflow | RDS endpoint |
| `DB_NAME` | K8s manifest | Database name (`bjj`) |

## Secrets access (IRSA)

The pod runs under the `bjj-api-sa` service account, which is annotated with the IRSA role ARN provisioned by `bjj-infra`. This grants `secretsmanager:GetSecretValue` on `bjj-db-secret-v2` without any static credentials.

```
Pod → bjj-api-sa (K8s ServiceAccount)
            ↓  IRSA annotation
      bjj-irsa-role (AWS IAM Role)
            ↓  inline policy
      Secrets Manager: bjj-db-secret-v2
```

## Local development

```bash
cd app
pip install -r requirements.txt

# Requires AWS credentials with GetSecretValue on bjj-db-secret-v2
export SECRET_NAME=bjj-db-secret-v2
export AWS_REGION=us-east-1
export DB_HOST=<rds-endpoint>
export DB_NAME=bjj

uvicorn main:app --reload --port 8080
```
