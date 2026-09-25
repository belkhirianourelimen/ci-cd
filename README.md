# WellnessHub — Jenkins CI/CD Pipelines

![Jenkins](https://img.shields.io/badge/Jenkins-D24939?style=flat&logo=jenkins&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=flat&logo=kubernetes&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-FF9900?style=flat&logo=amazon-aws&logoColor=white)
![Spring Boot](https://img.shields.io/badge/Spring_Boot-6DB33F?style=flat&logo=spring-boot&logoColor=white)
![SonarQube](https://img.shields.io/badge/SonarQube-4E9BCD?style=flat&logo=sonarqube&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI_GPT--4o-412991?style=flat&logo=openai&logoColor=white)

> Pipelines Jenkins CI/CD pour le déploiement automatisé de l'application **WellnessHub** sur deux environnements : VM locale (Docker Compose + Kubernetes) et AWS (EC2 + ECR).

---

## Structure du repo

```
wellnesshub-cicd/
│
├── local/                          ← Pipelines VM locale
│   ├── Jenkinsfile                 ← Pipeline Docker Compose (backend)
│   └── Jenkinsfile-k8s             ← Pipeline Kubernetes (rollout auto)
│
├── aws/                            ← Pipeline AWS production
│   ├── Jenkinsfile                 ← Pipeline complet AWS
│   ├── ai_diagnostic.py            ← Diagnostic IA GPT-4o-mini
│   └── docker-compose-aws.yml      ← Docker Compose EC2 (logs CloudWatch)
│
├── .gitignore
└── README.md
```

---

## Vue d'ensemble de l'architecture CI/CD

```
Developer Push (GitHub)
        │
        │  Webhook → ngrok → Jenkins
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    ENVIRONNEMENT LOCAL                       │
│                                                              │
│  Pipeline 1 : local/Jenkinsfile                             │
│  ─────────────────────────────────────────────────────────  │
│  Clone → Detect Changes → Build (conditionnel)              │
│       → Push Registry :5000 → Docker Compose Deploy         │
│       → Init Databases → Verify → Cleanup (2 builds)        │
│       → Email → Trigger Pipeline 2 ↓                        │
│                                                              │
│  Pipeline 2 : local/Jenkinsfile-k8s                         │
│  ─────────────────────────────────────────────────────────  │
│  Verify Cluster → kubectl rollout restart                    │
│       → Wait Rollout → Verify Pods → Email                  │
└─────────────────────────────────────────────────────────────┘
        │
        │  (déploiement AWS séparé)
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    ENVIRONNEMENT AWS                         │
│                                                              │
│  Pipeline 3 : aws/Jenkinsfile                               │
│  ─────────────────────────────────────────────────────────  │
│  Checkout (backend + frontend)                               │
│       → SonarQube Analysis (qualité code)                    │
│       → Build Docker Images                                  │
│       → Trivy Security Scan (HIGH/CRITICAL)                  │
│       → Push to ECR                                         │
│       → Retrieve Secrets (AWS SSM)                          │
│       → Deploy to EC2 (SSH + docker-compose)                 │
│       → Email HTML + Diagnostic IA (si échec)               │
└─────────────────────────────────────────────────────────────┘
```

---

## Pipeline 1 — local/Jenkinsfile (Docker Compose)

### Stages

| Stage | Description |
|-------|-------------|
| Clone Repository | `git clone` branche `main` |
| Verify Environment | Docker + Docker Compose OK |
| Detect Changes | `git diff` — build conditionnel par service |
| Build Docker Images | Double tag `:latest` + `:build-N` |
| Push to Local Registry | Push vers `192.168.49.1:5000` |
| Deploy with Docker Compose | `down` + `up -d` |
| Initialize Databases | CREATE DATABASE idempotent (4 schemas) |
| Verify Deployment | `docker-compose ps` + curl Eureka |
| Cleanup | `image prune` + garde 2 derniers builds |

### Fonctionnalités clés

```groovy
// Build conditionnel — rebuild uniquement les services modifiés
env.BUILD_EUREKA = changed.contains('Eureka') ? 'true' : 'false'

// Double versioning des images
docker build -t wellness-eureka:latest -t wellness-eureka:build-42 ./Eureka

// Déclenchement automatique du pipeline K8s après succès
post { success { build job: 'wellnesshub-k8s-pipeline', wait: false } }
```

---

## Pipeline 2 — local/Jenkinsfile-k8s (Kubernetes)

### Stages

| Stage | Description |
|-------|-------------|
| Verify Cluster | `kubectl get nodes` + pods status |
| Check Images | `minikube image ls` |
| Deploy or Update | `kubectl rollout restart` |
| Wait for Rollout | `kubectl rollout status --timeout=180s` |
| Verify Pods | `kubectl get pods/svc -n wellnesshub` |

---

## Pipeline 3 — aws/Jenkinsfile (AWS Production)

### Stages

| Stage | Description |
|-------|-------------|
| Checkout | Clone backend + frontend GitHub |
| SonarQube Analysis | Analyse qualité Maven sur ExpertMS |
| Build Docker Images | Build eureka, gateway, expertms, front |
| Trivy Security Scan | Scan vulnérabilités HIGH/CRITICAL (non bloquant) |
| Push to ECR | Push vers AWS Elastic Container Registry |
| Retrieve DB Secrets | Lecture AWS SSM Parameter Store |
| Deploy to EC2 | SSH + `docker-compose pull && up -d` |

### Credentials Jenkins requis

| ID | Type | Usage |
|----|------|-------|
| `github-credentials` | Username/Password | Clone repo backend |
| `malek-github` | Username/Password | Clone repo frontend |
| `ec2-ssh-key` | SSH Key | Connexion EC2 |
| `openai-api-key` | Secret Text | Diagnostic IA |

### Services AWS utilisés

| Service AWS | Usage |
|-------------|-------|
| ECR | Registry des images Docker |
| EC2 | Hébergement de l'application |
| SSM Parameter Store | Stockage sécurisé des secrets DB |
| CloudWatch Logs | Centralisation des logs applicatifs |

---

## Diagnostic IA — aws/ai_diagnostic.py

En cas d'échec du pipeline AWS, un diagnostic automatique est généré via **OpenAI GPT-4o-mini** :

```
Build échoue
    ↓
Jenkins récupère les 150 dernières lignes de logs
    ↓
ai_diagnostic.py analyse via GPT-4o-mini
    ↓
Rapport structuré :
  🔴 CAUSE RACINE
  🔍 ANALYSE DÉTAILLÉE
  ✅ ACTIONS CORRECTIVES (1, 2, 3)
  ⚡ NIVEAU DE CRITICITÉ
  💡 CONSEIL
    ↓
Email HTML enrichi → your-email@example.com
```

```python
# Usage manuel
export OPENAI_API_KEY="sk-..."
python3 aws/ai_diagnostic.py jenkins_failure.log "Build Docker Images" "42"
```

---

## docker-compose-aws.yml

Déployé sur EC2 via SSH. Particularités :

- Images depuis **AWS ECR** (variables `${ECR_REGISTRY}`, `${PROJECT_NAME}`)
- Credentials DB depuis **AWS SSM** (variables `${DB_ENDPOINT}`, `${DB_USERNAME}`, `${DB_PASSWORD}`)
- Logs centralisés dans **AWS CloudWatch** (`awslogs` driver)
- `restart: always` pour la haute disponibilité

---

## Configuration Jenkins

### Webhook GitHub

```
URL    : https://<your-ngrok-url>.ngrok-free.dev/github-webhook/
Type   : application/json
Events : Push only
```

### Plugins Jenkins requis

- Git Plugin
- Pipeline Plugin
- SSH Agent Plugin
- Email Extension Plugin
- SonarQube Scanner Plugin
- Credentials Plugin

---

## Choix techniques

| Décision | Justification |
|----------|---------------|
| 3 pipelines séparés | Séparation local/AWS — environnements indépendants |
| Build conditionnel (local) | Evite de rebuilder 6 services pour 1 fichier modifié |
| Cascade local → K8s | Garantit que les images existent avant le rollout K8s |
| Trivy non bloquant (`exit-code 0`) | Scan informatif — ne bloque pas le déploiement |
| SSM Parameter Store | Secrets DB jamais en clair dans le pipeline |
| Diagnostic IA GPT-4o-mini | Réduction du temps de debug — diagnostic immédiat |
| CloudWatch Logs | Centralisation des logs EC2 sans agent supplémentaire |

---

## Liens utiles

- 📦 [Manifests Kubernetes](https://github.com/belkhirianourelimen/k8s-manifests)
- 🏗️ [Infrastructure Terraform AWS](https://github.com/belkhirianourelimen/aws-infra-terraform.git)

---

*Nour El Imen Belkhiria — 2026*
