# RepoJudge Demo Audit

This Markdown file mirrors the bundled JSON demo. Start the application and choose **View sample
report** for the complete interactive report.

- README credibility: 73/100
- Production readiness: 62/100
- Learning value: 81/100
- Wrapper index: 28/100

The report is intentionally synthetic and clearly labeled as a demo; RepoJudge never presents it as
the result of a live repository scan.

## Claims

- Verified: Docker deployment
- Partial: complete tests
- Verified: multi-agent workflow
- Unsupported: vector retrieval
- Partial: production readiness

## Engineering and security

- README, license, pytest, Docker and type checking are present.
- CI and `.env.example` are missing.
- The demo includes two medium findings: broad CORS and debug enabled by default.

## Conclusion

The project contains real orchestration and tests, but its retrieval claim has no code evidence.
