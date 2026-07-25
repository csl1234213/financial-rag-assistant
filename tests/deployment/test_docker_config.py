import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import yaml


class TestDockerComposeStructure:
    def test_prod_compose_exists(self):
        compose_path = ROOT / "docker-compose.prod.yml"
        assert compose_path.exists(), "docker-compose.prod.yml not found"

    def test_prod_compose_has_nginx(self):
        compose_path = ROOT / "docker-compose.prod.yml"
        with open(compose_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "services" in data
        assert "nginx" in data["services"]

    def test_prod_compose_has_api(self):
        compose_path = ROOT / "docker-compose.prod.yml"
        with open(compose_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "api" in data["services"]

    def test_prod_compose_has_worker(self):
        compose_path = ROOT / "docker-compose.prod.yml"
        with open(compose_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "worker" in data["services"]

    def test_prod_compose_has_postgres(self):
        compose_path = ROOT / "docker-compose.prod.yml"
        with open(compose_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "postgres" in data["services"]

    def test_prod_compose_has_redis(self):
        compose_path = ROOT / "docker-compose.prod.yml"
        with open(compose_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "redis" in data["services"]

    def test_prod_compose_has_chromadb(self):
        compose_path = ROOT / "docker-compose.prod.yml"
        with open(compose_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "chromadb" in data["services"]

    def test_api_healthcheck_configured(self):
        compose_path = ROOT / "docker-compose.prod.yml"
        with open(compose_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        api = data["services"]["api"]
        assert "healthcheck" in api

    def test_nginx_depends_on_api(self):
        compose_path = ROOT / "docker-compose.prod.yml"
        with open(compose_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        nginx = data["services"]["nginx"]
        assert "depends_on" in nginx
        assert "api" in nginx["depends_on"]


class TestDockerfile:
    def test_dockerfile_exists(self):
        dockerfile_path = ROOT / "Dockerfile"
        assert dockerfile_path.exists(), "Dockerfile not found"

    def test_dockerfile_is_multi_stage(self):
        dockerfile_path = ROOT / "Dockerfile"
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "AS builder" in content
        assert "AS runtime" in content
        assert "AS api" in content
        assert "AS worker" in content

    def test_dockerfile_has_non_root_user(self):
        dockerfile_path = ROOT / "Dockerfile"
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "appuser" in content

    def test_dockerfile_has_healthcheck(self):
        dockerfile_path = ROOT / "Dockerfile"
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "HEALTHCHECK" in content

    def test_dockerfile_uses_python_311(self):
        dockerfile_path = ROOT / "Dockerfile"
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "python:3.11" in content


class TestNginxConfig:
    def test_nginx_conf_exists(self):
        nginx_path = ROOT / "deploy" / "nginx" / "nginx.conf"
        assert nginx_path.exists(), "deploy/nginx/nginx.conf not found"

    def test_nginx_has_gzip(self):
        nginx_path = ROOT / "deploy" / "nginx" / "nginx.conf"
        with open(nginx_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "gzip on" in content

    def test_nginx_has_security_headers(self):
        nginx_path = ROOT / "deploy" / "nginx" / "nginx.conf"
        with open(nginx_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "X-Content-Type-Options" in content
        assert "X-Frame-Options" in content

    def test_nginx_proxies_to_api(self):
        nginx_path = ROOT / "deploy" / "nginx" / "nginx.conf"
        with open(nginx_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "proxy_pass" in content
        assert "backend" in content


class TestEnvConfig:
    def test_env_example_exists(self):
        env_path = ROOT / ".env.example"
        assert env_path.exists()

    def test_env_production_exists(self):
        env_path = ROOT / ".env.production"
        assert env_path.exists()

    def test_env_test_exists(self):
        env_path = ROOT / ".env.test"
        assert env_path.exists()

    def test_env_example_has_required_keys(self):
        env_path = ROOT / ".env.example"
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        required = [
            "DATABASE_URL",
            "REDIS_URL",
            "SECRET_KEY",
            "DEEPSEEK_API_KEY",
            "LLM_MODEL_NAME",
        ]
        for key in required:
            assert key in content, f"Missing key in .env.example: {key}"

    def test_env_production_has_required_keys(self):
        env_path = ROOT / ".env.production"
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        required = [
            "APP_ENV=production",
            "DATABASE_URL=postgresql://",
            "REDIS_URL=redis://",
        ]
        for key in required:
            assert key in content, f"Missing key in .env.production: {key}"


class TestCIWorkflow:
    def test_production_workflow_exists(self):
        workflow_path = ROOT / ".github" / "workflows" / "production.yml"
        assert workflow_path.exists()

    def test_production_workflow_has_test(self):
        workflow_path = ROOT / ".github" / "workflows" / "production.yml"
        with open(workflow_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "test" in content.lower()

    def test_production_workflow_has_lint(self):
        workflow_path = ROOT / ".github" / "workflows" / "production.yml"
        with open(workflow_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "lint" in content.lower()

    def test_production_workflow_has_docker_build(self):
        workflow_path = ROOT / ".github" / "workflows" / "production.yml"
        with open(workflow_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "docker-build" in content or "docker build" in content.lower()


class TestBackupScript:
    def test_backup_script_exists(self):
        backup_path = ROOT / "scripts" / "backup_db.py"
        assert backup_path.exists()

    def test_backup_script_supports_postgresql(self):
        backup_path = ROOT / "scripts" / "backup_db.py"
        with open(backup_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "pg_dump" in content
        assert "postgresql" in content

    def test_backup_script_supports_sqlite(self):
        backup_path = ROOT / "scripts" / "backup_db.py"
        with open(backup_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "sqlite" in content.lower()

    def test_backup_script_has_cleanup(self):
        backup_path = ROOT / "scripts" / "backup_db.py"
        with open(backup_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "cleanup" in content.lower()
