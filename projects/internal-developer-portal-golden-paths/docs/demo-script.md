# Demo script

1. Open Pathfinder (standalone or from the portfolio hub). With hub demo data the catalog holds `ledger-worker` and `payments-api`, and **Artifact evidence** shows the stored `payments-api` archive: files with SHA-256 digests, the archive checksum, and a ZIP download.
2. Select `ledger-worker` in the **Service catalog** to switch the evidence panel to its archive.
3. Pick a golden path, enter a new service name, owner, and port, and click **Preview files** to see the validated file list.
4. Click **Generate artifact**, download the ZIP, and open the manifest.
5. Try an invalid name (for example `Bad_Name`) or port (`80`) to show server-side validation.
6. Mention the boundary: artifacts are ZIP files; there is no SCM integration and no generated hook is ever executed.
