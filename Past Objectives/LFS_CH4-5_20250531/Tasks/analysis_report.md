=== LFS Build Script Analysis Sat May 31 15:23:49 UTC 2025 ===
Scanning LFSBuilder directory structure...
LFSBuilder
├── Archives
│   └── LFSBUILDER.zip
├── BuildScripts
│   ├── add_sudo_rule.sh.README
│   ├── archive
│   ├── ch10_*
│   ├── ch11_*
│   ├── ch2_*
│   ├── ch3_*
│   ├── ch3_packages
│   │   ├── config.sh
│   │   ├── functions
│   │   │   ├── checksum_verification.sh
│   │   │   ├── download_manager.sh
│   │   │   ├── package_tracker.sh
│   │   │   └── patch_manager.sh
│   │   └── main.sh
│   ├── ch4_*
│   ├── ch5_*
│   ├── ch7_*
│   ├── ch8_*
│   ├── ch9_*
│   ├── common
│   ├── lfs-cli
│   ├── old_scripts
│   │   ├── 00_prep_binutils_pass1.sh
│   │   ├── 00_prep_gcc_pass1.sh
│   │   ├── 01_configure_binutils_pass1.sh
│   │   ├── 01_configure_gcc_pass1.sh
│   │   ├── 02_build_binutils_pass1.sh
│   │   ├── 02_build_gcc_pass1.sh
│   │   ├── 03_install_binutils_pass1.sh
│   │   ├── 03_install_gcc_pass1.sh
│   │   ├── add_sudo_rule.sh
│   │   ├── build-libstdcpp-pass1.sh
│   │   ├── build-tar.sh
│   │   ├── build-xz.sh
│   │   ├── build_coreutils.sh
│   │   ├── build_diffutils.sh
│   │   ├── build_env.sh
│   │   ├── build_file.sh
│   │   ├── build_gawk.sh
│   │   ├── build_gcc.sh
│   │   ├── build_gcc_pass1.sh
│   │   ├── build_glibc.sh
│   │   ├── build_grep.sh
│   │   ├── build_libstdcpp_pass1.sh
│   │   ├── build_ncurses.sh
│   │   ├── build_sed.sh
│   │   ├── ch6_bash_temp_toolchain.sh
│   │   ├── ch6_diffutils_temp_toolchain.sh
│   │   ├── ch6_m4_install.sh
│   │   ├── ch6_m4_temp_toolchain.sh
│   │   ├── ch6_ncurses_temp_toolchain.sh
│   │   ├── ch6_ncurses_temp_toolchain_modified.sh
│   │   ├── coreutils_temp_tools.sh
│   │   ├── diffutils_build.sh
│   │   ├── diffutils_temp_toolchain.sh
│   │   ├── file_temp_toolchain.sh
│   │   ├── findutils-4.10.0-build.sh
│   │   ├── findutils_temp_toolchain.sh
│   │   ├── fix_ncurses_symlinks.sh
│   │   ├── fix_permissions.sh
│   │   ├── gawk_temp_toolchain.sh
│   │   ├── gcc-pass2-build.sh
│   │   ├── gcc-pass2-extract.sh
│   │   ├── gcc_pass2_build.sh
│   │   ├── gcc_pass2_configure.sh
│   │   ├── gcc_pass2_extract.sh
│   │   ├── gcc_pass2_install.sh
│   │   ├── gcc_sanity_check.sh
│   │   ├── glibc.sh
│   │   ├── grep_temp_toolchain.sh
│   │   ├── lfs_setup.sh
│   │   ├── lfscli.sh
│   │   ├── libstdc++.sh
│   │   ├── patch_temp_toolchain.sh
│   │   ├── phase1_cross_toolchain.sh
│   │   ├── prepare_gcc_config.sh
│   │   ├── sed_temp_toolchain.sh
│   │   ├── set_permissions.sh
│   │   ├── setup_gcc_symlinks.sh
│   │   ├── setup_lfs_env.sh
│   │   ├── setup_lfsbuilder.sh
│   │   ├── temp_tools_build.sh
│   │   ├── toolchain_env.sh
│   │   ├── validate_env.sh
│   │   └── version-check.sh
│   ├── setup_lfsbuilder.README.md
│   ├── temp_tools_build.sh.bak
│   └── tests
│       ├── test_chapter3.sh
│       ├── test_common.sh
│       └── test_framework.sh
├── Config
│   ├── lfs_config.sh
│   └── variables.sh
├── Documentation
│   ├── Beyond-Linux-From-Scratch.html
│   ├── Beyond-Linux-From-Scratch.html.verified
│   ├── Core_Toolchain.md
│   ├── Framework
│   │   ├── README.md
│   │   ├── Sections
│   │   │   ├── D_BuildProcess.md
│   │   │   ├── E_TestingFramework.md
│   │   │   ├── F_InstallationProcedures.md
│   │   │   ├── section_a_template.md
│   │   │   ├── section_b_template.md
│   │   │   ├── section_c_template.md
│   │   │   ├── section_d_template.md
│   │   │   ├── section_e_template.md
│   │   │   ├── section_f_template.md
│   │   │   ├── section_g_template.md
│   │   │   ├── section_h_template.md
│   │   │   ├── section_i_template.md
│   │   │   └── section_j_template.md
│   │   ├── TEMPLATE.md
│   │   ├── config
│   │   │   ├── ai_integration.yaml
│   │   │   └── quality_metrics.yaml
│   │   ├── section_A_template.md
│   │   ├── section_B_template.md
│   │   └── section_C_template.md
│   ├── Linux From Scratch.html
│   ├── README.md
│   ├── analyze_html.py
│   ├── analyze_structure.py
│   ├── blfs_builder
│   │   └── usage.md
│   ├── blfs_builder_tasks.md
│   ├── build_status.md
│   ├── chapter1
│   │   ├── README.md
│   │   ├── chapter01.md
│   │   ├── chapter1_handler.sh
│   │   ├── commands
│   │   │   ├── reporting.md
│   │   │   ├── setup.sh
│   │   │   └── support.md
│   │   ├── configs
│   │   │   ├── lfs_info.md
│   │   │   └── troubleshooting.md
│   │   ├── packages
│   │   │   └── packages.md
│   │   └── scripts
│   │       ├── README.md
│   │       ├── disk-check.log
│   │       ├── disk-check.sh
│   │       ├── environment-check.log
│   │       ├── environment-check.sh
│   │       ├── metadata.json
│   │       ├── permission-check.log
│   │       ├── permission-check.sh
│   │       ├── setup.sh
│   │       ├── version-check.log
│   │       └── version-check.sh
│   ├── chapter10
│   │   ├── README.md
│   │   ├── chapter10.md
│   │   ├── commands
│   │   │   └── chapter10.sh
│   │   ├── configs
│   │   ├── overview.md
│   │   ├── packages
│   │   └── scripts
│   ├── chapter11
│   │   ├── README.md
│   │   ├── chapter11.md
│   │   ├── commands
│   │   ├── configs
│   │   ├── packages
│   │   │   └── system-completion.md
│   │   └── scripts
│   ├── chapter11.sh
│   ├── chapter12
│   │   ├── README.md
│   │   ├── commands
│   │   ├── configs
│   │   ├── dependencies
│   │   │   └── dependency_tracking.md
│   │   ├── index.md
│   │   ├── packages
│   │   │   ├── 7zip.md
│   │   │   ├── README.md
│   │   │   ├── accountsservice.md
│   │   │   ├── acpid.md
│   │   │   ├── at.md
│   │   │   ├── autofs.md
│   │   │   ├── bluez.md
│   │   │   ├── bubblewrap.md
│   │   │   ├── colord.md
│   │   │   ├── package_order.md
│   │   │   └── template.md
│   │   └── scripts
│   │       └── build-7zip.sh
│   ├── chapter13
│   ├── chapter14
│   ├── chapter15
│   ├── chapter16
│   ├── chapter17
│   ├── chapter18
│   ├── chapter19
│   ├── chapter2
│   │   ├── README.md
│   │   ├── chapter02.md
│   │   ├── chapter2_log.txt
│   │   ├── commands
│   │   │   ├── README.md
│   │   │   ├── environment.md
│   │   │   ├── setup.sh
│   │   │   ├── setup_instructions.md
│   │   │   └── version_check.sh
│   │   ├── configs
│   │   │   ├── filesystem.md
│   │   │   ├── mounting.md
│   │   │   └── partitioning.md
│   │   ├── packages
│   │   │   └── host_requirements.md
│   │   └── scripts
│   │       ├── metadata.json
│   │       ├── setup.sh
│   │       └── version_check.sh
│   ├── chapter20
│   ├── chapter21
│   ├── chapter22
│   ├── chapter23
│   ├── chapter24
│   ├── chapter25
│   ├── chapter26
│   ├── chapter27
│   ├── chapter28
│   ├── chapter29
│   ├── chapter3
│   │   ├── README.md
│   │   ├── chapter03.md
│   │   ├── commands
│   │   │   ├── README.md
│   │   │   ├── check_security.sh
│   │   │   └── download.sh
│   │   ├── configs
│   │   │   └── setup.md
│   │   ├── packages
│   │   │   ├── download_instructions.md
│   │   │   └── package_list.md
│   │   ├── patches
│   │   │   ├── optional_patches.md
│   │   │   └── required_patches.md
│   │   └── scripts
│   │       ├── chapter3_status.log
│   │       ├── check_security.sh
│   │       ├── download.log
│   │       ├── download.sh
│   │       ├── metadata.json
│   │       └── security_check.log
│   ├── chapter30
│   ├── chapter31
│   ├── chapter32
│   ├── chapter33
│   ├── chapter34
│   ├── chapter35
│   ├── chapter36
│   ├── chapter37
│   ├── chapter38
│   ├── chapter39
│   ├── chapter4
│   │   ├── README.md
│   │   ├── chapter04.md
│   │   ├── commands
│   │   │   ├── README.md
│   │   │   ├── build_instructions.md
│   │   │   ├── setup.sh
│   │   │   ├── shell_setup.md
│   │   │   └── user_setup.md
│   │   ├── configs
│   │   │   ├── build_environment.md
│   │   │   ├── directory_setup.md
│   │   │   └── test_suites.md
│   │   ├── packages
│   │   ├── scripts
│   │   │   ├── metadata.json
│   │   │   └── setup.sh
│   │   └── technical
│   │       └── toolchain_notes.md
│   ├── chapter40
│   ├── chapter5
│   │   ├── README.md
│   │   ├── chapter05.md
│   │   ├── chapter5_log.txt
│   │   ├── commands
│   │   │   ├── README.md
│   │   │   ├── build.sh
│   │   │   ├── package_scripts.md
│   │   │   └── sanity_check.md
│   │   ├── configs
│   │   │   ├── build_order.md
│   │   │   └── toolchain_overview.md
│   │   ├── packages
│   │   │   ├── binutils_pass1.md
│   │   │   ├── gcc_pass1.md
│   │   │   ├── glibc.md
│   │   │   ├── libstdcpp.md
│   │   │   ├── linux-headers.md
│   │   │   └── linux_headers.md
│   │   └── scripts
│   │       ├── build.log
│   │       ├── build.sh
│   │       └── metadata.json
│   ├── chapter6
│   │   ├── README.md
│   │   ├── build_chapter6.sh
│   │   ├── chapter06.md
│   │   ├── commands
│   │   │   ├── common_commands.md
│   │   │   └── environment_prep.md
│   │   ├── configs
│   │   │   ├── build_order.md
│   │   │   └── chapter_overview.md
│   │   ├── packages
│   │   │   ├── bash.md
│   │   │   ├── binutils_pass2.md
│   │   │   ├── coreutils.md
│   │   │   ├── diffutils.md
│   │   │   ├── file.md
│   │   │   ├── findutils.md
│   │   │   ├── gawk.md
│   │   │   ├── gcc_pass2.md
│   │   │   ├── grep.md
│   │   │   ├── gzip.md
│   │   │   ├── m4.md
│   │   │   ├── ncurses.md
│   │   │   ├── patch.md
│   │   │   ├── sed.md
│   │   │   ├── tar.md
│   │   │   └── xz.md
│   │   └── scripts
│   ├── chapter7
│   │   ├── README.md
│   │   ├── backup
│   │   │   └── backup_restore.md
│   │   ├── chapter07.md
│   │   ├── chapter7_log.txt
│   │   ├── chroot
│   │   │   ├── directory_structure.md
│   │   │   ├── setup.md
│   │   │   └── virtual_filesystems.md
│   │   ├── commands
│   │   ├── configs
│   │   │   ├── system_files.md
│   │   │   └── user_setup.md
│   │   ├── packages
│   │   │   ├── bison.md
│   │   │   ├── gettext.md
│   │   │   ├── perl.md
│   │   │   ├── python.md
│   │   │   ├── texinfo.md
│   │   │   └── util-linux.md
│   │   └── scripts
│   ├── chapter8
│   │   ├── README.md
│   │   ├── chapter08.md
│   │   ├── commands
│   │   ├── configs
│   │   ├── install.sh
│   │   ├── install.sh.new
│   │   ├── packages
│   │   │   ├── bash.log
│   │   │   ├── coreutils.log
│   │   │   ├── diffutils.log
│   │   │   ├── final-config.log
│   │   │   ├── gcc.log
│   │   │   ├── glibc.log
│   │   │   ├── m4.log
│   │   │   ├── make.log
│   │   │   ├── openssl.log
│   │   │   ├── perl.log
│   │   │   ├── shadow.log
│   │   │   ├── stripping.log
│   │   │   ├── udev-network.log
│   │   │   ├── udev.log
│   │   │   └── zlib.log
│   │   └── scripts
│   ├── chapter9
│   │   ├── README.md
│   │   ├── chapter09.md
│   │   ├── commands
│   │   ├── configs
│   │   ├── overview.md
│   │   ├── packages
│   │   └── scripts
│   ├── commands
│   │   ├── chapter7.sh
│   │   └── system-finalization.md
│   ├── config
│   │   ├── config -> ../../config
│   │   └── finalize.conf.template
│   ├── convert_lfs.py
│   ├── download_logs
│   │   ├── blfs_download_20250530_064607.log
│   │   ├── blfs_download_20250530_064709.log
│   │   ├── blfs_download_20250530_064741.log
│   │   ├── blfs_download_20250530_064844.log
│   │   ├── blfs_download_20250530_065013.log
│   │   ├── blfs_download_20250530_065108.log
│   │   ├── blfs_download_20250530_065938.log
│   │   ├── blfs_download_20250530_070045.log
│   │   ├── debug_20250530_064709
│   │   ├── debug_20250530_064742
│   │   │   └── index.html
│   │   ├── debug_20250530_064844
│   │   │   ├── BLFS-BOOK.html
│   │   │   ├── chapter12.html
│   │   │   └── index.html
│   │   ├── debug_20250530_065013
│   │   │   └── index.html
│   │   ├── debug_20250530_065108
│   │   ├── debug_20250530_065938
│   │   │   ├── chapter12.html
│   │   │   └── index.html
│   │   └── debug_20250530_070045
│   ├── gcc_build_process.md
│   ├── gcc_pass2_build.md
│   ├── host_requirements.md
│   ├── jhalfs.md
│   ├── jhalfs_documentation.md
│   ├── lfs-markdown
│   │   ├── README.md
│   │   ├── chapter01.md
│   │   ├── chapter02.md
│   │   ├── chapter03.md
│   │   ├── chapter04.md
│   │   ├── chapter05.md
│   │   ├── chapter06.md
│   │   ├── chapter07.md
│   │   ├── chapter08.md
│   │   ├── chapter09.md
│   │   ├── chapter10.md
│   │   └── chapter11.md
│   ├── lfs_warp_interface.py
│   ├── package_documentation
│   │   ├── build_order
│   │   ├── chapter10
│   │   │   └── chapter10_log.txt
│   │   ├── chapter1_comprehensive.md
│   │   ├── chapter2_comprehensive.md
│   │   ├── chapter3.md
│   │   ├── chapter6
│   │   │   └── chapter6_log.txt
│   │   ├── logs
│   │   │   ├── README.md
│   │   │   ├── chapter3
│   │   │   │   ├── chapter3_status.log -> ../../../../book/chapter3/scripts/chapter3_status.log
│   │   │   │   ├── download.log -> ../../../../book/chapter3/scripts/download.log
│   │   │   │   └── security_check.log -> ../../../../book/chapter3/scripts/security_check.log
│   │   │   └── index.md
│   │   ├── master_index.md
│   │   ├── packages
│   │   │   ├── binutils
│   │   │   │   └── info.md
│   │   │   ├── gcc
│   │   │   │   ├── info.md
│   │   │   │   └── libstdc++.md
│   │   │   ├── glibc
│   │   │   │   └── info.md
│   │   │   └── linux
│   │   │       └── info.md
│   │   └── patches
│   │       ├── coreutils-9.6-i18n-1.patch.md
│   │       └── glibc-2.41-fhs-1.patch.md
│   ├── partition_setup.md
│   ├── patch_analysis.md
│   ├── pkgmgt_doc.md
│   ├── post_process.py
│   ├── processed
│   ├── rules.md
│   ├── run-chapter9.sh
│   ├── run_as_lfs.md
│   ├── scripts
│   │   ├── ch8_binutils_pass2.sh
│   │   ├── chapter-helper.sh
│   │   ├── chapter5_scripts.md
│   │   ├── fetch-blfs-book.sh
│   │   ├── finalize-system.sh
│   │   └── validate-config.sh
│   ├── scripts.md
│   ├── test_package
│   │   ├── A.md
│   │   ├── B.md
│   │   ├── C.md
│   │   ├── D.md
│   │   ├── E.md
│   │   ├── F.md
│   │   ├── G.md
│   │   ├── H.md
│   │   ├── I.md
│   │   └── J.md
│   ├── verification
│   │   ├── first-boot-check.sh
│   │   └── network-verification.md
│   ├── version-check.sh
│   └── {chapter12..chapter40}
├── Logs
│   ├── 2025-05-29-001054.log
│   ├── 2025-05-29-001056.log
│   ├── 2025-05-29-010210_gcc_script.md
│   ├── 2025-05-29-010215_gcc_script_creation.md
│   ├── 2025-05-29_000126_glibc_fhs_patch.md
│   ├── 2025-05-29_12-03_setup_lfsbuilder.log
│   ├── 2025-05-29_12-03_setup_lfsbuilder_created.log
│   ├── 2025-05-29_12-03_setup_lfsbuilder_update.log
│   ├── 2025-05-29_12-07_location_change.log
│   ├── 2025-05-29_setup_lfsbuilder.log
│   ├── 20250528.log
│   ├── 20250528_223934_glibc_restart.log
│   ├── 20250528_224743_gcc_pass1_completion.log
│   ├── 20250528_224752_linux_headers_start.log
│   ├── 20250528_224825_linux_headers_completion.log
│   ├── 20250528_224836_linux_headers_verification.log
│   ├── 20250528_224845_linux_headers_final.log
│   ├── 20250528_224904_glibc_start.log
│   ├── 20250528_224913_glibc_config.log
│   ├── 20250528_224923_glibc_build.log
│   ├── 20250528_225455_glibc_extract.log
│   ├── 20250528_225503_glibc_config.log
│   ├── 20250528_225503_glibc_config_output.log
│   ├── 20250528_225518_linux_headers.log
│   ├── 20250528_225537_linux_headers.log
│   ├── 20250528_225558_linux_headers_install.log
│   ├── 20250528_230546_linux_headers.log
│   ├── 20250528_230546_linux_headers_build.log
│   ├── 20250528_230617_glibc.log
│   ├── 20250528_230617_glibc_build.log
│   ├── 20250528_230645_glibc.log
│   ├── 20250528_230645_glibc_build.log
│   ├── 20250528_230720_linux_headers.log
│   ├── 20250528_230720_linux_headers_build.log
│   ├── 20250528_230826_glibc.log
│   ├── 20250528_230826_glibc_build.log
│   ├── 20250528_231522_status.log
│   ├── 20250528_231531_gcc_pass2_start.log
│   ├── 20250528_231554_gcc_pass2_restart.log
│   ├── 20250528_231555_gcc_pass2_configure.log
│   ├── 20250528_231602_gcc_pass2_build.log
│   ├── 20250528_231602_gcc_pass2_build_output.log
│   ├── 20250528_231638_gcc_pass2_build_output.log
│   ├── 20250528_231638_gcc_pass2_restart.log
│   ├── 20250528_232331_gcc_pass2_build_output.log
│   ├── 20250528_232449_gcc_pass2.log
│   ├── 20250528_233007_gcc_pass1.log
│   ├── 20250529_000957_gcc_pass2.log
│   ├── 20250529_011409_gcc_pass2_scripts.log
│   ├── 20250529_011425_gcc_pass2_extract.log
│   ├── 20250529_011437_gcc_pass2_configure.log
│   ├── 20250529_011454_gcc_pass2_configure.log
│   ├── 20250529_011502_gcc_pass2_build.log
│   ├── 20250529_011502_gcc_pass2_build_output.log
│   ├── 20250529_012016_gcc_pass2_build_complete.log
│   ├── 20250529_013324_gcc_pass2_install.log
│   ├── 20250529_013329_gcc_pass2_install.log
│   ├── 20250529_013545_gcc_pass2_install.log
│   ├── 20250529_013621_gcc_pass2_install.log
│   ├── 20250529_013653_gcc_pass2_dependency.log
│   ├── 20250529_013803_gcc_pass2_prerequisite.log
│   ├── 20250529_035326_binutils_pass2_setup.log
│   ├── 20250529_115536_binutils_pass2_scripts.log
│   ├── 20250529_115537_binutils_pass2_extract_creation.log
│   ├── 20250529_115538_binutils_pass2_configure_creation.log
│   ├── 20250529_115539_binutils_pass2_build_creation.log
│   ├── 20250529_115540_binutils_pass2_install_creation.log
│   ├── 20250529_115541_binutils_pass2_master_setup.log
│   ├── README.md
│   ├── bash-temp-toolchain-20250529-211118.log
│   ├── bash-temp-toolchain-20250529-211254.log
│   ├── binutils-pass1-20250529-234916.log
│   ├── binutils-pass1-build-20250529-130705.log
│   ├── binutils-pass1-configure-20250529-130656.log
│   ├── binutils-pass1-configure-20250529-231039.log
│   ├── binutils-pass1-configure-20250529-231259.log
│   ├── binutils-pass1-configure-20250529-231543.log
│   ├── binutils-pass1-configure-20250529-231618.log
│   ├── binutils-pass1-configure-20250529-231707.log
│   ├── binutils-pass1-install-20250529-130806.log
│   ├── binutils-pass1-prep-20250529-130608.log
│   ├── binutils-pass1-prep-20250529-130649.log
│   ├── binutils-pass1-prep-20250529-230928.log
│   ├── binutils-pass1-prep-20250529-231037.log
│   ├── binutils-pass1-prep-20250529-231114.log
│   ├── binutils-pass1-prep-20250529-231257.log
│   ├── binutils-pass1-prep-20250529-231418.log
│   ├── binutils-pass1-prep-20250529-231505.log
│   ├── binutils-pass1-prep-20250529-231543.log
│   ├── binutils-pass1-prep-20250529-231618.log
│   ├── binutils-pass1-prep-20250529-231707.log
│   ├── binutils_pass1_20250528_223841.log
│   ├── build_20250528_223432.log
│   ├── build_20250528_223518.log
│   ├── build_20250528_223610.log
│   ├── build_20250528_223707.log
│   ├── build_20250528_223802.log
│   ├── buildlogs
│   │   ├── README.md
│   │   ├── bash-temp-toolchain-20250529-211118.log
│   │   ├── bash-temp-toolchain-20250529-211254.log
│   │   ├── binutils-pass1-20250529-234916.log
│   │   ├── binutils-pass1-build-20250529-130705.log
│   │   ├── binutils-pass1-configure-20250529-130656.log
│   │   ├── binutils-pass1-configure-20250529-231039.log
│   │   ├── binutils-pass1-configure-20250529-231259.log
│   │   ├── binutils-pass1-configure-20250529-231543.log
│   │   ├── binutils-pass1-configure-20250529-231618.log
│   │   ├── binutils-pass1-configure-20250529-231707.log
│   │   ├── binutils-pass1-install-20250529-130806.log
│   │   ├── binutils-pass1-prep-20250529-130608.log
│   │   ├── binutils-pass1-prep-20250529-130649.log
│   │   ├── binutils-pass1-prep-20250529-230928.log
│   │   ├── binutils-pass1-prep-20250529-231037.log
│   │   ├── binutils-pass1-prep-20250529-231114.log
│   │   ├── binutils-pass1-prep-20250529-231257.log
│   │   ├── binutils-pass1-prep-20250529-231418.log
│   │   ├── binutils-pass1-prep-20250529-231505.log
│   │   ├── binutils-pass1-prep-20250529-231543.log
│   │   ├── binutils-pass1-prep-20250529-231618.log
│   │   ├── binutils-pass1-prep-20250529-231707.log
│   │   ├── checksum_report.txt
│   │   ├── checksum_verification.log
│   │   ├── download_missing.log
│   │   ├── gcc-pass1-20250529-235052.log
│   │   ├── gcc-pass1-20250529-235121.log
│   │   ├── gcc-pass1-20250529-235145.log
│   │   ├── gcc-pass1-20250529-235227.log
│   │   ├── gcc-pass1-20250529-235334.log
│   │   ├── gcc-pass1-20250529-235442.log
│   │   ├── gcc-pass1-configure-20250529-131337.log
│   │   ├── gcc-pass1-configure-20250529-131918.log
│   │   ├── gcc-pass1-prep-20250529-130945.log
│   │   ├── gcc-pass1-prep-20250529-131016.log
│   │   ├── gcc-pass1-prep-20250529-131752.log
│   │   ├── gcc_build_20250529_010632.log
│   │   ├── gcc_build_20250529_010636.log
│   │   ├── glibc-20250530-000442.log
│   │   ├── glibc-20250530-000835.log
│   │   ├── glibc-20250530-001259.log
│   │   ├── lfs-setup-20250529-183311.log
│   │   ├── lfs-setup-20250529-183321.log
│   │   ├── lfs-setup-20250529-183347.log
│   │   ├── lfs-setup-20250529-183409.log
│   │   ├── lfs_env_20250529-130608.log
│   │   ├── lfs_env_20250529-130649.log
│   │   ├── lfs_env_20250529-130656.log
│   │   ├── lfs_env_20250529-130705.log
│   │   ├── lfs_env_20250529-130806.log
│   │   ├── lfs_env_20250529-130945.log
│   │   ├── lfs_env_20250529-224940.log
│   │   ├── lfs_env_20250529-225234.log
│   │   ├── lfs_env_20250529-225423.log
│   │   ├── lfs_env_20250529-225641.log
│   │   ├── lfs_env_20250529-225836.log
│   │   ├── lfs_env_20250529-230004.log
│   │   ├── libstdcpp-pass1-20250530-001818.log
│   │   ├── libstdcxx_build_20250529_164600.log
│   │   ├── libstdcxx_build_20250529_164716.log
│   │   ├── libstdcxx_build_20250529_164908.log
│   │   ├── libstdcxx_build_20250529_165135.log
│   │   ├── libstdcxx_build_20250529_165443.log
│   │   ├── libstdcxx_build_20250529_165538.log
│   │   ├── libstdcxx_build_20250529_170358.log
│   │   ├── libstdcxx_build_20250529_170540.log
│   │   ├── libstdcxx_build_20250529_172141.log
│   │   ├── libstdcxx_build_20250529_172622.log
│   │   ├── libstdcxx_build_20250529_172856.log
│   │   ├── libstdcxx_build_20250529_173130.log
│   │   ├── libstdcxx_build_20250529_173315.log
│   │   ├── linux-headers-20250530-000248.log
│   │   ├── linux-headers-20250530-000336.log
│   │   ├── lsblk_scan_20250529-130539.log
│   │   ├── mount_snapshot_20250529-130539.log
│   │   ├── ncurses-temp-toolchain-20250529-210210.log
│   │   ├── ncurses-temp-toolchain-20250529-210334.log
│   │   ├── ncurses-temp-toolchain-20250529-210347.log
│   │   ├── ncurses-temp-toolchain-20250529-210419.log
│   │   ├── ncurses-temp-toolchain-20250529-210501.log
│   │   ├── ncurses-temp-toolchain-20250529-210600.log
│   │   ├── phase1-20250529-231905.log
│   │   ├── phase1_cross_toolchain_20250529-224728.log
│   │   ├── phase1_cross_toolchain_20250529-224940.log
│   │   ├── phase1_cross_toolchain_20250529-225234.log
│   │   ├── phase1_cross_toolchain_20250529-225423.log
│   │   ├── phase1_cross_toolchain_20250529-225641.log
│   │   ├── phase1_cross_toolchain_20250529-225836.log
│   │   ├── phase1_cross_toolchain_20250529-230004.log
│   │   ├── phase2_build_20250529_225824.log
│   │   ├── phase2_build_20250529_225829.log
│   │   ├── phase2_build_20250529_225834.log
│   │   ├── phase2_error_20250529_225824.log
│   │   ├── phase2_error_20250529_225829.log
│   │   ├── phase2_error_20250529_225834.log
│   │   ├── phase2_progress
│   │   └── temp-tools
│   │       ├── build_logs
│   │       ├── checkpoints
│   │       └── error_logs
│   ├── buildstatus
│   │   ├── 20250528_224743_gcc_pass1_completion.log
│   │   ├── 20250528_224752_linux_headers_start.log
│   │   ├── 20250528_224825_linux_headers_completion.log
│   │   ├── 20250528_224836_linux_headers_verification.log
│   │   ├── 20250528_224845_linux_headers_final.log
│   │   ├── 20250528_224904_glibc_start.log
│   │   ├── 20250528_224913_glibc_config.log
│   │   ├── 20250528_224923_glibc_build.log
│   │   ├── 20250528_225455_glibc_extract.log
│   │   ├── 20250528_225503_glibc_config.log
│   │   ├── 20250528_225503_glibc_config_output.log
│   │   ├── 20250528_225518_linux_headers.log
│   │   ├── 20250528_225537_linux_headers.log
│   │   ├── 20250528_225558_linux_headers_install.log
│   │   ├── 20250528_230546_linux_headers_build.log
│   │   ├── 20250528_230617_glibc_build.log
│   │   ├── 20250528_230645_glibc_build.log
│   │   ├── 20250528_230720_linux_headers_build.log
│   │   ├── 20250528_230826_glibc_build.log
│   │   ├── 20250528_231531_gcc_pass2_start.log
│   │   ├── 20250528_231554_gcc_pass2_restart.log
│   │   ├── 20250528_231555_gcc_pass2_configure.log
│   │   ├── 20250528_231602_gcc_pass2_build.log
│   │   ├── 20250528_231602_gcc_pass2_build_output.log
│   │   ├── 20250528_231638_gcc_pass2_build_output.log
│   │   ├── 20250528_231638_gcc_pass2_restart.log
│   │   ├── 20250528_232331_gcc_pass2_build_output.log
│   │   ├── 20250529_011425_gcc_pass2_extract.log
│   │   ├── 20250529_011437_gcc_pass2_configure.log
│   │   ├── 20250529_011454_gcc_pass2_configure.log
│   │   ├── 20250529_011502_gcc_pass2_build.log
│   │   ├── 20250529_011502_gcc_pass2_build_output.log
│   │   ├── 20250529_013324_gcc_pass2_install.log
│   │   ├── 20250529_013329_gcc_pass2_install.log
│   │   ├── 20250529_013545_gcc_pass2_install.log
│   │   ├── 20250529_013621_gcc_pass2_install.log
│   │   ├── 20250529_013803_gcc_pass2_prerequisite.log
│   │   ├── README.md
│   │   ├── gcc_build.log
│   │   ├── gcc_config.status
│   │   ├── gcc_pass2_20250529_000957.log
│   │   ├── gcc_pass2_status_20250529_000957
│   │   ├── glibc_fhs_patch_2025-05-29_000342.log
│   │   ├── glibc_fhs_patch_2025-05-29_000419.log
│   │   ├── glibc_fhs_patch_2025-05-29_000441.log
│   │   ├── linux_headers_start.log
│   │   ├── status_20250528_222826.log
│   │   ├── status_20250528_223253.log
│   │   ├── status_20250528_223259.log
│   │   ├── status_20250528_223341.log
│   │   ├── status_20250528_223432.log
│   │   ├── status_20250528_223518.log
│   │   ├── status_20250528_223610.log
│   │   ├── status_20250528_223628.log
│   │   ├── status_20250528_223707.log
│   │   ├── status_20250528_223721.log
│   │   ├── status_20250528_223802.log
│   │   ├── status_20250528_223855.log
│   │   ├── status_20250528_224003.log
│   │   └── status_20250528_224602.log
│   ├── change_20250529_011751.log
│   ├── changelogs
│   │   ├── 2025-05-29-001054.log
│   │   ├── 2025-05-29-001056.log
│   │   ├── 2025-05-29-010210_gcc_script.md
│   │   ├── 2025-05-29-010215_gcc_script_creation.md
│   │   ├── 2025-05-29_000126_glibc_fhs_patch.md
│   │   ├── 2025-05-29_12-03_setup_lfsbuilder.log
│   │   ├── 2025-05-29_12-03_setup_lfsbuilder_created.log
│   │   ├── 2025-05-29_12-03_setup_lfsbuilder_update.log
│   │   ├── 2025-05-29_12-07_location_change.log
│   │   ├── 20250528.log
│   │   ├── 20250528_223934_glibc_restart.log
│   │   ├── 20250528_230546_linux_headers.log
│   │   ├── 20250528_230617_glibc.log
│   │   ├── 20250528_230645_glibc.log
│   │   ├── 20250528_230720_linux_headers.log
│   │   ├── 20250528_230826_glibc.log
│   │   ├── 20250528_231522_status.log
│   │   ├── 20250528_232449_gcc_pass2.log
│   │   ├── 20250528_233007_gcc_pass1.log
│   │   ├── 20250529_000957_gcc_pass2.log
│   │   ├── 20250529_011409_gcc_pass2_scripts.log
│   │   ├── 20250529_012016_gcc_pass2_build_complete.log
│   │   ├── 20250529_013653_gcc_pass2_dependency.log
│   │   ├── 20250529_035326_binutils_pass2_setup.log
│   │   ├── 20250529_115536_binutils_pass2_scripts.log
│   │   ├── 20250529_115537_binutils_pass2_extract_creation.log
│   │   ├── 20250529_115538_binutils_pass2_configure_creation.log
│   │   ├── 20250529_115539_binutils_pass2_build_creation.log
│   │   ├── 20250529_115540_binutils_pass2_install_creation.log
│   │   ├── 20250529_115541_binutils_pass2_master_setup.log
│   │   ├── binutils_pass1_20250528_223841.log
│   │   ├── build_20250528_223432.log
│   │   ├── build_20250528_223518.log
│   │   ├── build_20250528_223610.log
│   │   ├── build_20250528_223707.log
│   │   ├── build_20250528_223802.log
│   │   ├── change_20250529_011751.log
│   │   ├── gcc_build_20250529_002047.log
│   │   ├── gcc_build_20250529_003017.log
│   │   ├── gcc_build_20250529_003127.log
│   │   ├── gcc_build_20250529_003253.log
│   │   ├── gcc_build_20250529_003555.log
│   │   ├── gcc_changes_20250529_010632.log
│   │   ├── gcc_changes_20250529_010636.log
│   │   ├── gcc_config_20250529_001854.log
│   │   ├── gcc_config_20250529_001912.log
│   │   ├── gcc_config_20250529_001937.log
│   │   ├── gcc_config_20250529_001957.log
│   │   ├── gcc_config_20250529_002020.log
│   │   ├── gcc_config_20250529_002042.log
│   │   ├── gcc_pass1_build.log
│   │   ├── gcc_symlinks_20250529_001937.log
│   │   ├── gcc_symlinks_20250529_001958.log
│   │   ├── gcc_symlinks_20250529_002020.log
│   │   ├── gcc_symlinks_20250529_002043.log
│   │   ├── glibc_build.log
│   │   ├── headers_build.log
│   │   ├── init_20250528_222826.log
│   │   └── init_20250528_223253.log
│   ├── checksum_report.txt
│   ├── checksum_verification.log
│   ├── download_missing.log
│   ├── gcc-pass1-20250529-235052.log
│   ├── gcc-pass1-20250529-235121.log
│   ├── gcc-pass1-20250529-235145.log
│   ├── gcc-pass1-20250529-235227.log
│   ├── gcc-pass1-20250529-235334.log
│   ├── gcc-pass1-20250529-235442.log
│   ├── gcc-pass1-configure-20250529-131337.log
│   ├── gcc-pass1-configure-20250529-131918.log
│   ├── gcc-pass1-prep-20250529-130945.log
│   ├── gcc-pass1-prep-20250529-131016.log
│   ├── gcc-pass1-prep-20250529-131752.log
│   ├── gcc_build.log
│   ├── gcc_build_20250529_002047.log
│   ├── gcc_build_20250529_003017.log
│   ├── gcc_build_20250529_003127.log
│   ├── gcc_build_20250529_003253.log
│   ├── gcc_build_20250529_003555.log
│   ├── gcc_build_20250529_010632.log
│   ├── gcc_build_20250529_010636.log
│   ├── gcc_changes_20250529_010632.log
│   ├── gcc_changes_20250529_010636.log
│   ├── gcc_config.status
│   ├── gcc_config_20250529_001854.log
│   ├── gcc_config_20250529_001912.log
│   ├── gcc_config_20250529_001937.log
│   ├── gcc_config_20250529_001957.log
│   ├── gcc_config_20250529_002020.log
│   ├── gcc_config_20250529_002042.log
│   ├── gcc_master.log
│   ├── gcc_pass1_build.log
│   ├── gcc_pass2_20250529_000957.log
│   ├── gcc_pass2_status_20250529_000957
│   ├── gcc_symlinks_20250529_001937.log
│   ├── gcc_symlinks_20250529_001958.log
│   ├── gcc_symlinks_20250529_002020.log
│   ├── gcc_symlinks_20250529_002043.log
│   ├── glibc-20250530-000442.log
│   ├── glibc-20250530-000835.log
│   ├── glibc-20250530-001259.log
│   ├── glibc_build.log
│   ├── glibc_fhs_patch_2025-05-29_000342.log
│   ├── glibc_fhs_patch_2025-05-29_000419.log
│   ├── glibc_fhs_patch_2025-05-29_000441.log
│   ├── headers_build.log
│   ├── init_20250528_222826.log
│   ├── init_20250528_223253.log
│   ├── lfs-setup-20250529-183311.log
│   ├── lfs-setup-20250529-183321.log
│   ├── lfs-setup-20250529-183347.log
│   ├── lfs-setup-20250529-183409.log
│   ├── lfs_env_20250529-130608.log
│   ├── lfs_env_20250529-130649.log
│   ├── lfs_env_20250529-130656.log
│   ├── lfs_env_20250529-130705.log
│   ├── lfs_env_20250529-130806.log
│   ├── lfs_env_20250529-130945.log
│   ├── lfs_env_20250529-224940.log
│   ├── lfs_env_20250529-225234.log
│   ├── lfs_env_20250529-225423.log
│   ├── lfs_env_20250529-225641.log
│   ├── lfs_env_20250529-225836.log
│   ├── lfs_env_20250529-230004.log
│   ├── libstdcpp-pass1-20250530-001818.log
│   ├── libstdcxx_build_20250529_164600.log
│   ├── libstdcxx_build_20250529_164716.log
│   ├── libstdcxx_build_20250529_164908.log
│   ├── libstdcxx_build_20250529_165135.log
│   ├── libstdcxx_build_20250529_165443.log
│   ├── libstdcxx_build_20250529_165538.log
│   ├── libstdcxx_build_20250529_170358.log
│   ├── libstdcxx_build_20250529_170540.log
│   ├── libstdcxx_build_20250529_172141.log
│   ├── libstdcxx_build_20250529_172622.log
│   ├── libstdcxx_build_20250529_172856.log
│   ├── libstdcxx_build_20250529_173130.log
│   ├── libstdcxx_build_20250529_173315.log
│   ├── linux-headers-20250530-000248.log
│   ├── linux-headers-20250530-000336.log
│   ├── linux_headers_start.log
│   ├── lsblk_scan_20250529-130539.log
│   ├── master.log
│   ├── master_changelog.md
│   ├── master_changes.log
│   ├── masterlog
│   │   ├── 2025-05-29_setup_lfsbuilder.log
│   │   ├── gcc_master.log
│   │   ├── master.log
│   │   ├── master_changelog.md
│   │   ├── master_changes.log
│   │   ├── masterlog.txt
│   │   ├── version-check-20250528-170516.log
│   │   ├── version-check-20250528-170612.log
│   │   ├── version-check-20250528-170702.log
│   │   ├── version-check-20250528-222929.log
│   │   ├── version-check-20250528-222933.log
│   │   ├── version-check-20250528-223020.log
│   │   └── version-check-20250528-223129.log
│   ├── masterlog.txt
│   ├── mount_snapshot_20250529-130539.log
│   ├── ncurses-temp-toolchain-20250529-210210.log
│   ├── ncurses-temp-toolchain-20250529-210334.log
│   ├── ncurses-temp-toolchain-20250529-210347.log
│   ├── ncurses-temp-toolchain-20250529-210419.log
│   ├── ncurses-temp-toolchain-20250529-210501.log
│   ├── ncurses-temp-toolchain-20250529-210600.log
│   ├── phase1-20250529-231905.log
│   ├── phase1_cross_toolchain_20250529-224728.log
│   ├── phase1_cross_toolchain_20250529-224940.log
│   ├── phase1_cross_toolchain_20250529-225234.log
│   ├── phase1_cross_toolchain_20250529-225423.log
│   ├── phase1_cross_toolchain_20250529-225641.log
│   ├── phase1_cross_toolchain_20250529-225836.log
│   ├── phase1_cross_toolchain_20250529-230004.log
│   ├── phase2_build_20250529_225824.log
│   ├── phase2_build_20250529_225829.log
│   ├── phase2_build_20250529_225834.log
│   ├── phase2_error_20250529_225824.log
│   ├── phase2_error_20250529_225829.log
│   ├── phase2_error_20250529_225834.log
│   ├── phase2_progress
│   ├── status_20250528_222826.log
│   ├── status_20250528_223253.log
│   ├── status_20250528_223259.log
│   ├── status_20250528_223341.log
│   ├── status_20250528_223432.log
│   ├── status_20250528_223518.log
│   ├── status_20250528_223610.log
│   ├── status_20250528_223628.log
│   ├── status_20250528_223707.log
│   ├── status_20250528_223721.log
│   ├── status_20250528_223802.log
│   ├── status_20250528_223855.log
│   ├── status_20250528_224003.log
│   ├── status_20250528_224602.log
│   ├── temp-tools
│   │   ├── build_logs
│   │   ├── checkpoints
│   │   └── error_logs
│   ├── version-check-20250528-170516.log
│   ├── version-check-20250528-170612.log
│   ├── version-check-20250528-170702.log
│   ├── version-check-20250528-222929.log
│   ├── version-check-20250528-222933.log
│   ├── version-check-20250528-223020.log
│   └── version-check-20250528-223129.log
├── NEXT_STEPS.md
├── Resources
├── Source
└── Tools
    ├── README.md
    ├── assessment_config.yml
    ├── collect_metrics.sh
    └── validate_docs.sh

161 directories, 819 files

Script inventory:
LFSBuilder/Documentation/chapter8/install.sh
LFSBuilder/Documentation/commands/chapter7.sh
LFSBuilder/Documentation/chapter12/scripts/build-7zip.sh
LFSBuilder/Documentation/chapter1/chapter1_handler.sh
LFSBuilder/Documentation/chapter1/commands/setup.sh
LFSBuilder/Documentation/chapter1/scripts/permission-check.sh
LFSBuilder/Documentation/chapter1/scripts/disk-check.sh
LFSBuilder/Documentation/chapter1/scripts/environment-check.sh
LFSBuilder/Documentation/chapter1/scripts/version-check.sh
LFSBuilder/Documentation/chapter1/scripts/setup.sh
LFSBuilder/Documentation/chapter3/commands/download.sh
LFSBuilder/Documentation/chapter3/commands/check_security.sh
LFSBuilder/Documentation/chapter3/scripts/download.sh
LFSBuilder/Documentation/chapter3/scripts/check_security.sh
LFSBuilder/Documentation/scripts/chapter-helper.sh
LFSBuilder/Documentation/scripts/validate-config.sh
LFSBuilder/Documentation/scripts/finalize-system.sh
LFSBuilder/Documentation/scripts/fetch-blfs-book.sh
LFSBuilder/Documentation/scripts/ch8_binutils_pass2.sh
LFSBuilder/Documentation/chapter6/build_chapter6.sh
LFSBuilder/Documentation/chapter5/commands/build.sh
LFSBuilder/Documentation/chapter5/scripts/build.sh
LFSBuilder/Documentation/chapter11.sh
LFSBuilder/Documentation/chapter2/commands/version_check.sh
LFSBuilder/Documentation/chapter2/commands/setup.sh
LFSBuilder/Documentation/chapter2/scripts/version_check.sh
LFSBuilder/Documentation/chapter2/scripts/setup.sh
LFSBuilder/Documentation/run-chapter9.sh
LFSBuilder/Documentation/version-check.sh
LFSBuilder/Documentation/chapter4/commands/setup.sh
LFSBuilder/Documentation/chapter4/scripts/setup.sh
LFSBuilder/Documentation/verification/first-boot-check.sh
LFSBuilder/Documentation/chapter10/commands/chapter10.sh
LFSBuilder/BuildScripts/ch3_packages/main.sh
LFSBuilder/BuildScripts/ch3_packages/functions/checksum_verification.sh
LFSBuilder/BuildScripts/ch3_packages/functions/package_tracker.sh
LFSBuilder/BuildScripts/ch3_packages/functions/download_manager.sh
LFSBuilder/BuildScripts/ch3_packages/functions/patch_manager.sh
LFSBuilder/BuildScripts/ch3_packages/config.sh
LFSBuilder/BuildScripts/old_scripts/gcc_pass2_build.sh
LFSBuilder/BuildScripts/old_scripts/01_configure_gcc_pass1.sh
LFSBuilder/BuildScripts/old_scripts/gcc_pass2_extract.sh
LFSBuilder/BuildScripts/old_scripts/patch_temp_toolchain.sh
LFSBuilder/BuildScripts/old_scripts/build_ncurses.sh
LFSBuilder/BuildScripts/old_scripts/validate_env.sh
LFSBuilder/BuildScripts/old_scripts/build_sed.sh
LFSBuilder/BuildScripts/old_scripts/gcc_sanity_check.sh
LFSBuilder/BuildScripts/old_scripts/03_install_gcc_pass1.sh
LFSBuilder/BuildScripts/old_scripts/ch6_m4_temp_toolchain.sh
LFSBuilder/BuildScripts/old_scripts/ch6_diffutils_temp_toolchain.sh
LFSBuilder/BuildScripts/old_scripts/diffutils_temp_toolchain.sh
LFSBuilder/BuildScripts/old_scripts/findutils_temp_toolchain.sh
LFSBuilder/BuildScripts/old_scripts/gcc_pass2_install.sh
LFSBuilder/BuildScripts/old_scripts/setup_lfsbuilder.sh
LFSBuilder/BuildScripts/old_scripts/coreutils_temp_tools.sh
LFSBuilder/BuildScripts/old_scripts/ch6_ncurses_temp_toolchain_modified.sh
LFSBuilder/BuildScripts/old_scripts/add_sudo_rule.sh
LFSBuilder/BuildScripts/old_scripts/build_libstdcpp_pass1.sh
LFSBuilder/BuildScripts/old_scripts/build_grep.sh
LFSBuilder/BuildScripts/old_scripts/sed_temp_toolchain.sh
LFSBuilder/BuildScripts/old_scripts/03_install_binutils_pass1.sh
LFSBuilder/BuildScripts/old_scripts/toolchain_env.sh
LFSBuilder/BuildScripts/old_scripts/file_temp_toolchain.sh
LFSBuilder/BuildScripts/old_scripts/glibc.sh
LFSBuilder/BuildScripts/old_scripts/build_gcc.sh
LFSBuilder/BuildScripts/old_scripts/gcc-pass2-build.sh
LFSBuilder/BuildScripts/old_scripts/lfscli.sh
LFSBuilder/BuildScripts/old_scripts/build_file.sh
LFSBuilder/BuildScripts/old_scripts/setup_gcc_symlinks.sh
LFSBuilder/BuildScripts/old_scripts/fix_permissions.sh
LFSBuilder/BuildScripts/old_scripts/diffutils_build.sh
LFSBuilder/BuildScripts/old_scripts/grep_temp_toolchain.sh
LFSBuilder/BuildScripts/old_scripts/prepare_gcc_config.sh
LFSBuilder/BuildScripts/old_scripts/set_permissions.sh
LFSBuilder/BuildScripts/old_scripts/02_build_gcc_pass1.sh
LFSBuilder/BuildScripts/old_scripts/build_env.sh
LFSBuilder/BuildScripts/old_scripts/findutils-4.10.0-build.sh
LFSBuilder/BuildScripts/old_scripts/build_glibc.sh
LFSBuilder/BuildScripts/old_scripts/setup_lfs_env.sh
LFSBuilder/BuildScripts/old_scripts/00_prep_binutils_pass1.sh
LFSBuilder/BuildScripts/old_scripts/build-libstdcpp-pass1.sh
LFSBuilder/BuildScripts/old_scripts/ch6_ncurses_temp_toolchain.sh
LFSBuilder/BuildScripts/old_scripts/temp_tools_build.sh
LFSBuilder/BuildScripts/old_scripts/01_configure_binutils_pass1.sh
LFSBuilder/BuildScripts/old_scripts/fix_ncurses_symlinks.sh
LFSBuilder/BuildScripts/old_scripts/gcc_pass2_configure.sh
LFSBuilder/BuildScripts/old_scripts/ch6_bash_temp_toolchain.sh
LFSBuilder/BuildScripts/old_scripts/phase1_cross_toolchain.sh
LFSBuilder/BuildScripts/old_scripts/gcc-pass2-extract.sh
LFSBuilder/BuildScripts/old_scripts/libstdc++.sh
LFSBuilder/BuildScripts/old_scripts/build-tar.sh
LFSBuilder/BuildScripts/old_scripts/build_gawk.sh
LFSBuilder/BuildScripts/old_scripts/version-check.sh
LFSBuilder/BuildScripts/old_scripts/ch6_m4_install.sh
LFSBuilder/BuildScripts/old_scripts/build-xz.sh
LFSBuilder/BuildScripts/old_scripts/gawk_temp_toolchain.sh
LFSBuilder/BuildScripts/old_scripts/lfs_setup.sh
LFSBuilder/BuildScripts/old_scripts/build_diffutils.sh
LFSBuilder/BuildScripts/old_scripts/00_prep_gcc_pass1.sh
LFSBuilder/BuildScripts/old_scripts/02_build_binutils_pass1.sh
LFSBuilder/BuildScripts/old_scripts/build_coreutils.sh
LFSBuilder/BuildScripts/old_scripts/build_gcc_pass1.sh
LFSBuilder/BuildScripts/tests/test_framework.sh
LFSBuilder/BuildScripts/tests/test_chapter3.sh
LFSBuilder/BuildScripts/tests/test_common.sh
LFSBuilder/Tools/validate_docs.sh
LFSBuilder/Tools/collect_metrics.sh
LFSBuilder/Config/lfs_config.sh
LFSBuilder/Config/variables.sh
