SHELL := /bin/bash
PY := agent/.venv/bin/python

.PHONY: dev dev-agent dev-api dev-web build deploy deploy-ec2 deploy-web

## Run agent worker + case API + web UI together (Ctrl-C stops all)
dev:
	./scripts/dev.sh

dev-agent:
	cd agent && .venv/bin/python main.py dev

dev-api:
	cd api && ../agent/.venv/bin/python -m uvicorn main:app --reload --port 8090

dev-web:
	cd web && npm run dev

## Gate: python imports + Next.js production build
build:
	$(PY) -c "import sys; sys.path.insert(0, 'agent'); import main, disha; print('agent OK')"
	$(PY) -c "import sys; sys.path.insert(0, 'api'); import main; print('api OK')"
	cd web && npm run build

## Worker + API to EC2, web to Vercel
deploy: deploy-ec2 deploy-web

deploy-ec2:
	./scripts/deploy-ec2.sh

deploy-web:
	cd web && npx vercel --prod
