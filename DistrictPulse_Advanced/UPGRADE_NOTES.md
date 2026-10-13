# Upgrading an existing DistrictPulse-AI Git repository

This source bundle is based on the uploaded `DistrictPulse_Advanced_Clean_Demo` source. It does not include `.git`, generated SUMO networks, experiment outputs, virtual environments, or model checkpoints.

## Safest way to apply it

1. Back up your current project folder.
2. Extract this ZIP into a separate temporary folder.
3. Copy/merge the following items from the extracted `DistrictPulse_Advanced` folder into your existing Git repository:
   - `.gitignore`, `README.md`, `run_demo.ps1`
   - `districtpulse/`
   - `scripts/`
   - `tests/`
   - `docs/`
   - `requirements.txt`
4. Do **not** delete or replace your existing `.git` folder.
5. Keep your existing `.venv` if desired, then run `pip install -r requirements.txt`.
6. Follow `README.md` from section 3 onward one command at a time.
7. Run `python -m pytest tests -q` before committing.
8. Review `git status` and `git diff` before staging changes.

The emergency behavior is a simulation prototype. Validate the generated ambulance route and signal transitions in SUMO-GUI before making any real-world safety claim.
