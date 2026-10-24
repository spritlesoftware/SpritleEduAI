from edupilot import plan

def test_plan_selfcheck(capsys):
    import runpy; runpy.run_path(plan.__file__, run_name="__main__")
