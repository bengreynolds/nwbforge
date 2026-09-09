# Development Environment Baseline

Purpose: define the current development and test environment policy.

Current baseline:
- Use the dedicated Conda environment from `environment.yml`
- Support `minimal`, `selected`, and `full` install modes, but always target the dedicated environment
- Do not rely on user-site packages for development or test success

Constraints:
- Release artifacts must remain self-contained
- Development bootstrap should stay environment-specific rather than arbitrary-active-shell specific

Next step:
- Change this note only when install or test policy changes
