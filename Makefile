.PHONY: all test test-cov verify eval eval-rag eval-solver eval-intent eval-forecast eval-ablation report build clean

all: test eval build

test:
	python -m pytest backend/tests/ -v

test-cov:
	python -m pytest backend/tests/ --cov=backend/app --cov-report=term-missing -v

verify:
	python verify_system.py

eval: eval-rag eval-solver eval-intent eval-forecast eval-ablation
	python scripts/build_report.py

eval-rag:
	python scripts/eval_rag.py --seed 42

eval-solver:
	python scripts/eval_solver.py --seed 42 --n 50

eval-intent:
	python scripts/eval_intent.py

eval-forecast:
	python scripts/eval_forecast.py

eval-ablation:
	python scripts/eval_ablation.py --seed 42

report:
	python scripts/build_report.py

build:
	cd frontend && npm run build

clean:
	rm -rf .pytest_cache .coverage backend/.pytest_cache frontend/dist
