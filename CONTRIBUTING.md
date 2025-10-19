# Contributing to Truce 🚀

Thank you for your interest in contributing to **Truce**! Your help — whether it’s finding bugs, proposing a new feature, improving documentation, or submitting code — is greatly appreciated.

## What kind of contributions do we welcome  
- Bug reports: Something is broken or not behaving as expected.  
- Feature requests: Ideas to improve Truce’s functionality or usability.  
- Documentation improvements: Clarify concepts, correct typos, add examples.  
- Code contributions: Fix bugs, add tests, implement features, refactor.  
- Quality, performance & maintenance: Improve build/test tooling, CI, code health.

## First steps  
1. Fork the repository and clone your fork locally.  
   ```bash
   git clone https://github.com/<your‑username>/truce.git
   cd truce
   ```  
2. Create a new branch for your change:  
   ```bash
   git checkout ‑‑create <branch‑name>
   ```  
   Use a descriptive branch name: e.g., `fix‑issue‑123`, `feat‑new‑api`, `docs‑typo‑abc`.  
3. Make your changes. Add tests if relevant and ensure existing tests pass.  
4. Commit your changes with a clear commit message, e.g.  
   ```
   Fix: resolve panic when using nil payload  
   ```  
   Then push your branch:  
   ```bash
   git push origin <branch‑name>
   ```  
5. Open a Pull Request (PR) from your branch into the `main` (or appropriate) branch of this repo.  
   - Link the issue your PR addresses (if any).  
   - Provide context: what you changed, why, how to test.  
   - Follow the code style and existing patterns in the project.

## Filing Issues  
When opening a new issue, please include:  
- A descriptive title.  
- A clear description of the problem or suggestion.  
- Steps to reproduce (for bugs).  
- Expected vs. actual behavior.  
- Environment details (OS, version, dependencies) if relevant.  
- Any relevant logs, screenshots, or stack traces.

## Labels to know  
- `good‑first‑issue`: small task suitable for first‐time contributors.  
- `bug`: a confirmed bug needing a fix.  
- `enhancement`: new feature request or improvement.  
- `documentation`: work on docs, examples or tutorials.  
- `help‑wanted`: open for external contributions.

## Contribution guidelines & code of conduct  
By participating, you agree to abide by the project’s Code of Conduct. Please read [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) (if present) for details.

## Review process  
Once your PR is submitted:  
- A maintainer will review it as soon as possible; please be patient — open source maintenance takes time.  
- Feedback may be requested: please follow up.  
- Once approved, your change will be merged and you will be congratulated as a contributor! 🎉  
- After merge, it’s helpful if you delete your branch in your fork (cleanup).

## Thank you  
Your contributions help make Truce stronger, more robust, and more useful for everyone. Thanks for joining the journey.

— The Truce Maintainers
