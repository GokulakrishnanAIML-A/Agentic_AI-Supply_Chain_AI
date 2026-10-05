.PHONY: all test eval eval-rag eval-solver eval-intent eval-forecast eval-ablation build clean

all: test eval build

test:
	python -m pytest backend/tests/ -v

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

build:
	cd frontend && npm run build
