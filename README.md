# AWS Challenge

SPA (React + Vite) → Amplify Hosting · Cognito User Pool · API Gateway HTTP API (JWT authorizer) →
Lambda (Spring Boot 4, Java 21) in private subnets → RDS Proxy → PostgreSQL + pgvector · Bedrock Titan Embeddings ·
structured JSON logs in CloudWatch.

```
aws_challenge/
├── amplify.yml          Amplify Hosting build spec (monorepo, appRoot = frontend)
├── docker-compose.yml   local PostgreSQL 17 + pgvector
├── backend/             Spring Boot app, packaged as a Lambda zip
└── frontend/            React SPA (Amplify Auth UI, React Router, TanStack Query)
```

## Backend

| What | Where |
|---|---|
| Lambda handler for API Gateway (Chatbot + Admin functions) | `lambda/ApiLambdaHandler` |
| Cognito PostConfirmation trigger (Sync function) | `lambda/PostConfirmationHandler` |
| JWT claims from the API Gateway authorizer | `security/CurrentUserResolver` |
| Titan Text Embeddings v2 | `ai/EmbeddingService` |
| pgvector k-NN search (cosine, HNSW) | `document/DocumentRepository` |
| Schema, `CREATE EXTENSION vector`, HNSW / IVFFlat indexes | `resources/db/migration/V1__init.sql` |
| Correlation ids in MDC + access log | `web/RequestLoggingFilter` |
| JSON (ECS) logs | `application-lambda.properties` |

Routes: `GET /api/health` (public), `GET /api/me`, `POST /api/chat/search`, `GET /api/admin/users?page=&size=` (group `admin`).

Key dependencies: Spring Boot **4.0.8** (the line `aws-serverless-java-container-springboot4` 3.0.4 is built for),
`aws-serverless-java-container-springboot4`, `aws-lambda-java-core/events`, AWS SDK v2 BOM 2.57.2 (`bedrockruntime`,
`url-connection-client`), Flyway, `hibernate-vector`, PostgreSQL driver, Testcontainers 2.

### Run locally

```bash
docker compose up -d                                   # PostgreSQL + pgvector on :5432
./gradlew :backend:bootRun --args='--spring.profiles.active=local'
./gradlew :backend:test                                # needs Docker (Testcontainers)
```

Profile `local` returns a fake admin user, so the API works without Cognito. `/api/chat/search` calls Bedrock for real,
so it needs AWS credentials (`aws configure` / `AWS_PROFILE`) and model access to `amazon.titan-embed-text-v2:0`.

### Build the Lambda package

```bash
./gradlew :backend:buildZip       # -> backend/build/distributions/backend-lambda.zip
```

| Lambda | Handler | Runtime | Env |
|---|---|---|---|
| chatbot / admin | `com.scnsoft.max.aws_challenge.lambda.ApiLambdaHandler::handleRequest` | java21, 1024–2048 MB, timeout ≥ 30 s | `DB_URL`, `DB_USERNAME`, `DB_PASSWORD`, (`FLYWAY_ENABLED`) |
| sync | `com.scnsoft.max.aws_challenge.lambda.PostConfirmationHandler::handleRequest` | same | same |

`DB_URL=jdbc:postgresql://<rds-proxy-endpoint>:5432/aws_challenge`. Turn on **SnapStart** for the Java functions —
Spring cold starts are several seconds without it. Lambdas in private subnets have no internet access: add an
interface **VPC endpoint** for `bedrock-runtime` (and Secrets Manager, if you read the DB secret from there) or a NAT gateway.
CloudWatch Logs needs nothing extra — the Lambda service ships stdout for you.

## Frontend

```bash
cd frontend
cp .env.example .env.local       # fill Cognito ids; leave empty to skip login locally
npm install
npm run dev                      # http://localhost:5173, /api proxied to :8080
```

Calls send `Authorization: Bearer <Cognito ID token>`; the API Gateway JWT authorizer must use
issuer `https://cognito-idp.<region>.amazonaws.com/<userPoolId>` and audience `<appClientId>`.

## Notes on the architecture diagram

- The goal says **HTTP API** with a JWT authorizer, the diagram says REST — the handler uses HTTP API payload v2.
  For REST API switch to `SpringBootLambdaContainerHandler.getAwsProxyHandler(...)` and a Cognito authorizer.
- Cognito **PostConfirmation** invokes a Lambda directly; there is no native Cognito → EventBridge trigger.
- CloudFront is a global service, it does not live inside a VPC; Amplify Hosting already serves the SPA through CloudFront.
  "Inside a VPC" applies to Lambda, RDS Proxy and RDS (private subnets + security groups).
- **Bedrock Agent** (`InvokeAgent`) is streaming-only and needs an async HTTP client: add `bedrockagentruntime` +
  `aws-crt-client` when you get there, or use the synchronous Bedrock `Converse` API with Claude from `bedrockruntime`.
