"""Deterministic score weights. LLM assistance may never change more than 10 points."""

README_WEIGHTS = {
    "verified_claim_ratio": 60,
    "readme_present": 15,
    "startup_artifacts": 15,
    "unsupported_claim_penalty": 10,
}

PRODUCTION_WEIGHTS = {
    "tests": 8,
    "executable_tests": 6,
    "dockerfile": 8,
    "compose": 3,
    "env_example": 6,
    "logging": 7,
    "exceptions": 7,
    "health": 7,
    "ci": 8,
    "typing": 5,
    "pinned": 6,
    "readme_commands": 4,
    "hardcoded_paths": 4,
    "hardcoded_secrets": 8,
    "empty_implementations": 3,
    "security": 10,
}

LEARNING_WEIGHTS = {
    "readme": 20,
    "tests": 15,
    "typing": 10,
    "formatting": 10,
    "modularity": 25,
    "runnable": 20,
}

WRAPPER_WEIGHTS = {
    "small_codebase": 20,
    "model_api_usage": 25,
    "missing_tools": 15,
    "missing_data_pipeline": 15,
    "missing_state": 10,
    "missing_evaluation": 10,
    "claim_gap": 20,
}

MAX_LLM_ASSIST = 10
