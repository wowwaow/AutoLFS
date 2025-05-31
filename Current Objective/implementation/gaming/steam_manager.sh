#!/bin/bash

# Steam Integration Manager
# Provides Steam platform integration with game and workshop management

set -euo pipefail

# Configuration
GAMING_ROOT="/var/lib/lfs-wrapper/gaming"
GAMING_DB="${GAMING_ROOT}/gaming.db"
STEAM_ROOT="${GAMING_ROOT}/steam"
STEAM_APPS="${STEAM_ROOT}/steamapps"
WORKSHOP_DIR="${STEAM_ROOT}/workshop"

# Initialize Steam manager
init_steam_manager() {
    mkdir -p "${STEAM_ROOT}"
    mkdir -p "${STEAM_APPS}"
    mkdir -p "${WORKSHOP_DIR}"
    
    # Initialize Steam database
    sqlite3 "${GAMING_DB}" << 'EOF'
CREATE TABLE IF NOT EXISTS steam_installations (
    id INTEGER PRIMARY KEY,
    path TEXT,
    version TEXT,
    status TEXT,
    installed_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS steam_games (
    app_id INTEGER PRIMARY KEY,
    name TEXT,
    install_dir TEXT,
    proton_version TEXT,
    status TEXT,
    last_updated DATETIME
);

CREATE TABLE IF NOT EXISTS workshop_items (
    item_id INTEGER PRIMARY KEY,
    app_id INTEGER,
    name TEXT,
    status TEXT,
    installed_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(app_id) REFERENCES steam_games(app_id)
);

CREATE TABLE IF NOT EXISTS steam_play_config (
    app_id INTEGER PRIMARY KEY,
    proton_version TEXT,
    launch_options TEXT,
    custom_settings TEXT,
    FOREIGN KEY(app_id) REFERENCES steam_games(app_id)
);
EOF
}

# Steam installation management
manage_steam() {
    local action="$1"
    shift
    
    case "$action" in
        install)
            install_steam "$@"
            ;;
        update)
            update_steam "$@"
            ;;
        remove)
            remove_steam "$@"
            ;;
        repair)
            repair_steam "$@"
            ;;
    esac
}

install_steam() {
    local version="${1:-latest}"
    local path="${STEAM_ROOT}/steam-${version}"
    
    echo "Installing Steam version: $version"
    
    # Download and install Steam
    mkdir -p "$path"
    if download_steam "$version" "$path"; then
        # Record installation
        sqlite3 "${GAMING_DB}" << EOF
INSERT INTO steam_installations (path, version, status)
VALUES ('${path}', '${version}', 'installed');
EOF
        
        # Configure Steam
        configure_steam "$path"
        
        echo "Steam installation completed"
        return 0
    else
        echo "Steam installation failed"
        return 1
    fi
}

# Game management
manage_game() {
    local action="$1"
    local app_id="$2"
    shift 2
    
    case "$action" in
        install)
            install_game "$app_id" "$@"
            ;;
        update)
            update_game "$app_id"
            ;;
        remove)
            remove_game "$app_id"
            ;;
        verify)
            verify_game "$app_id"
            ;;
        configure)
            configure_game "$app_id" "$@"
            ;;
    esac
}

install_game() {
    local app_id="$1"
    local name="$2"
    local proton_version="${3:-}"
    
    echo "Installing game: $name (AppID: $app_id)"
    
    # Install game using Steam
    if steam_cmd +app_update "$app_id" validate +quit; then
        # Record installation
        sqlite3 "${GAMING_DB}" << EOF
INSERT INTO steam_games (app_id, name, install_dir, proton_version, status)
VALUES (
    ${app_id},
    '${name}',
    '${STEAM_APPS}/common/${name}',
    '${proton_version}',
    'installed'
);
EOF
        
        # Configure Proton if needed
        if [ -n "$proton_version" ]; then
            configure_proton_for_game "$app_id" "$proton_version"
        fi
        
        echo "Game installation completed"
        return 0
    else
        echo "Game installation failed"
        return 1
    fi
}

# Library configuration
configure_library() {
    local action="$1"
    shift
    
    case "$action" in
        add)
            add_library_folder "$@"
            ;;
        remove)
            remove_library_folder "$@"
            ;;
        scan)
            scan_library_folders
            ;;
        repair)
            repair_library "$@"
            ;;
    esac
}

add_library_folder() {
    local path="$1"
    
    echo "Adding Steam library folder: $path"
    
    # Create library folder
    mkdir -p "${path}/steamapps/common"
    
    # Configure Steam to use the folder
    steam_cmd +library_folder_add "$path" +quit
}

# Workshop support
manage_workshop() {
    local action="$1"
    local app_id="$2"
    shift 2
    
    case "$action" in
        subscribe)
            subscribe_workshop_item "$app_id" "$@"
            ;;
        unsubscribe)
            unsubscribe_workshop_item "$app_id" "$@"
            ;;
        update)
            update_workshop_items "$app_id"
            ;;
        list)
            list_workshop_items "$app_id"
            ;;
    esac
}

subscribe_workshop_item() {
    local app_id="$1"
    local item_id="$2"
    local name="$3"
    
    echo "Subscribing to workshop item: $name (ID: $item_id)"
    
    # Subscribe to item
    if steam_cmd +workshop_download_item "$app_id" "$item_id" +quit; then
        # Record subscription
        sqlite3 "${GAMING_DB}" << EOF
INSERT INTO workshop_items (item_id, app_id, name, status)
VALUES (${item_id}, ${app_id}, '${name}', 'subscribed');
EOF
        
        echo "Workshop item subscription completed"
        return 0
    else
        echo "Workshop item subscription failed"
        return 1
    fi
}

# Steam Play configuration
configure_steam_play() {
    local app_id="$1"
    local proton_version="$2"
    local launch_options="${3:-}"
    local custom_settings="${4:-}"
    
    echo "Configuring Steam Play for AppID: $app_id"
    
    # Configure Steam Play settings
    sqlite3 "${GAMING_DB}" << EOF
INSERT OR REPLACE INTO steam_play_config (app_id, proton_version, launch_options, custom_settings)
VALUES (${app_id}, '${proton_version}', '${launch_options}', '${custom_settings}');
EOF
    
    # Apply configuration
    apply_steam_play_config "$app_id"
}

# Helper functions
steam_cmd() {
    # Execute Steam command-line tool
    steamcmd "$@"
}

apply_steam_play_config() {
    local app_id="$1"
    
    # Get configuration
    local config
    config=$(sqlite3 "${GAMING_DB}" << EOF
SELECT proton_version, launch_options, custom_settings
FROM steam_play_config
WHERE app_id = ${app_id};
EOF
)
    
    # Apply configuration to Steam
    local proton_version=$(echo "$config" | cut -d'|' -f1)
    local launch_options=$(echo "$config" | cut -d'|' -f2)
    local custom_settings=$(echo "$config" | cut -d'|' -f3)
    
    # Update Steam configuration files
    update_steam_config "$app_id" "$proton_version" "$launch_options" "$custom_settings"
}

# Main functionality
main() {
    local command="$1"
    shift
    
    case "$command" in
        init)
            init_steam_manager
            ;;
        steam)
            manage_steam "$@"
            ;;
        game)
            manage_game "$@"
            ;;
        library)
            configure_library "$@"
            ;;
        workshop)
            manage_workshop "$@"
            ;;
        proton)
            configure_steam_play "$@"
            ;;
        *)
            echo "Unknown command: $command"
            exit 1
            ;;
    esac
}

# Execute if running directly
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi

