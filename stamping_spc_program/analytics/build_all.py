"""Build every figure, page and number trace from the marts.

Usage: python -m analytics.build_all
Run after the exports are loaded and the dbt project is built. Two consecutive runs give byte-identical outputs."""
import runpy

MODULES = ["analytics.reports.assessment", "analytics.reports.redesign_results", "analytics.control_plan.control_plan", "analytics.spc_board.spc_board", "analytics.dashboard.dashboard", "analytics.site"]


def main():
    for name in MODULES:
        print(name)
        runpy.run_module(name, run_name="__main__")


if __name__ == "__main__":
    main()
