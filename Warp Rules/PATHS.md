# PATHS.md — Warp System Directory & File Reference

This document provides a complete, versioned reference of all important system paths used by the Warp AI system and its managed projects.

---

## 📦 System Root

| Path                                           | Description                                  |
|------------------------------------------------|---------------------------------------------|
| `/home/ubuntu/Documents/WARP_CURRENT/`         | Root directory for Warp system operations    |

---

## 📂 Core Folders

| Path                                           | Purpose                                     |
|------------------------------------------------|---------------------------------------------|
| `/Warp Rules/`                                 | Holds `README.md` and `DOCUMENTATION.md`    |
| `/System Commands/`                            | Stores `COMMANDS.md` and command definitions |
| `/System Reports/`                             | Generated system status + cleanup reports   |
| `/Objective/Future Objective/`                 | Planned project phases                      |
| `/Objective/Current Objective/`                | Active working phase                        |
| `/Objective/Past Objective/`                   | Archived completed phases                   |
| `/Work Logs/`                                  | Agent logs, `MASTERLOG.md`, active/completed|
| `/Tasks/Future Tasks/`                         | Unassigned future tasks                     |
| `/Tasks/Current Tasks/`                        | Active tasks in progress                    |
| `/Tasks/Completed Tasks/`                      | Finished tasks archive                      |

---

## 📂 Project-Specific Paths

| Project Name               | Path Example                                       | Notes                                      |
|----------------------------|----------------------------------------------------|--------------------------------------------|
| Modular LFS Builder        | `/modular-lfs-builder-v1/`                         | Contains modular scripts, configs, outputs |
| Modular LFS Script Archive | `/modular-lfs-builder-v1/scripts/`                 | Stores chapter-by-chapter automation       |
| Modular LFS Outputs        | `/modular-lfs-builder-v1/build-outputs/`           | Built artifacts and logs                   |
| LFS Documentation          | `/home/ubuntu/Documents/LFS Documentation/`         | Core LFS system documentation and guides   |
| LFSbuilder                | `/home/ubuntu/Documents/LFSbuilder/`               | Build automation and tooling for LFS       |
| lfs_migration             | `/home/ubuntu/Documents/lfs_migration/`            | Migration tools and chapter documentation  |
| lfs_migration/chapter06   | `/home/ubuntu/Documents/lfs_migration/chapter06/`  | Chapter 6 build scripts and documentation  |
| lfs_migration/docs        | `/home/ubuntu/Documents/lfs_migration/docs/`       | Core documentation and access rules        |

---

## 📦 Standalone Files

| File Name                     | Path                                              | Purpose                                    |
|------------------------------|---------------------------------------------------|---------------------------------------------|
| WarpGPT.odt                 | `/home/ubuntu/Documents/WarpGPT.odt`              | Warp system documentation                   |
| lfs_backup_20250531.tar.gz  | `/home/ubuntu/Documents/lfs_backup_20250531.tar.gz` | LFS system backup from May 31, 2025        |
| lfsbuilder_original_docs.tar.gz | `/home/ubuntu/Documents/lfsbuilder_original_docs.tar.gz` | Original LFSbuilder documentation archive |

---

## 📄 Key Files

| File Path                                              | Description                                  |
|--------------------------------------------------------|---------------------------------------------|
| `/Warp Rules/README.md`                                | Main system ruleset                         |
| `/Warp Rules/DOCUMENTATION.md`                         | System overview + usage documentation       |
| `/System Commands/COMMANDS.md`                         | List of available system commands           |
| `/Work Logs/MASTERLOG.md`                              | Master coordination log across agents       |
| `/Work Logs/TASKS.csv`                                 | Master task assignment + status tracker     |
| `/Work Logs/agent_<name>.csv`                          | Per-agent live progress + heartbeat file    |
| `/Objective/Current Objective/CURRENTOBJECTIVE.md`     | Active phase description + instructions     |

---

## 🛡 Path Governance

✅ **All new projects or modules must:**
- Define their root directory under the Warp system
- Register all key subpaths in this `PATHS.md`
- Update `DOCUMENTATION.md` with integration notes
- Ensure agents reference canonical paths, not hardcoded strings

✅ **Why:**
- Ensures traceability, reproducibility, and maintainability
- Prevents lost or orphaned files
- Supports multi-agent coordination on shared resources

---

## 📈 Version Control

✅ This file is version-controlled alongside the Warp system and its projects.
✅ All path changes must be recorded wi




