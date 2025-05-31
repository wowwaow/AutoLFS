#!/bin/bash

# Graphics Optimization System
# Provides comprehensive graphics optimization and configuration management

set -euo pipefail

# Configuration
GAMING_ROOT="/var/lib/lfs-wrapper/gaming"
GAMING_DB="${GAMING_ROOT}/gaming.db"
CONFIG_DIR="${GAMING_ROOT}/gpu_configs"
PROFILE_DIR="${GAMING_ROOT}/gpu_profiles"

# Initialize graphics optimizer
init_graphics_optimizer() {
    mkdir -p "${CONFIG_DIR}"
    mkdir -p "${PROFILE_DIR}"
    
    # Initialize optimizer database
    sqlite3 "${GAMING_DB}" << 'EOF'
CREATE TABLE IF NOT EXISTS gpu_configs (
    name TEXT PRIMARY KEY,
    gpu_type TEXT,
    settings TEXT,
    performance_level TEXT,
    enabled INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS gpu_profiles (
    name TEXT PRIMARY KEY,
    description TEXT,
    base_config TEXT,
    custom_settings TEXT,
    FOREIGN KEY(base_config) REFERENCES gpu_configs(name)
);

CREATE TABLE IF NOT EXISTS gpu_performance (
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    profile TEXT,
    fps REAL,
    temperature REAL,
    power_usage REAL,
    memory_usage REAL,
    FOREIGN KEY(profile) REFERENCES gpu_profiles(name)
);
EOF
}

# Driver optimization
optimize_driver() {
    local gpu_type="$1"
    local profile="$2"
    
    echo "Optimizing driver for: $gpu_type ($profile)"
    
    # Get base configuration
    local base_config
    base_config=$(get_base_config "$gpu_type")
    
    # Apply profile-specific optimizations
    local profile_settings
    profile_settings=$(get_profile_settings "$profile")
    
    # Merge configurations
    local final_config
    final_config=$(merge_configurations "$base_config" "$profile_settings")
    
    # Apply configuration
    apply_gpu_config "$final_config"
    
    # Verify optimization
    verify_gpu_optimization
}

# Performance profiles
manage_gpu_profile() {
    local action="$1"
    local profile="$2"
    shift 2
    
    case "$action" in
        create)
            create_gpu_profile "$profile" "$@"
            ;;
        apply)
            apply_gpu_profile "$profile"
            ;;
        update)
            update_gpu_profile "$profile" "$@"
            ;;
        remove)
            remove_gpu_profile "$profile"
            ;;
    esac
}

create_gpu_profile() {
    local name="$1"
    local description="$2"
    local base_config="$3"
    local custom_settings="$4"
    
    # Create profile
    sqlite3 "${GAMING_DB}" << EOF
INSERT INTO gpu_profiles (name, description, base_config, custom_settings)
VALUES ('${name}', '${description}', '${base_config}', '${custom_settings}');
EOF
    
    # Generate profile configuration
    generate_gpu_profile_config "$name" > "${PROFILE_DIR}/${name}.conf"
}

# GPU configuration
configure_gpu() {
    local gpu_type="$1"
    local settings="$2"
    
    echo "Configuring GPU: $gpu_type"
    
    case "$gpu_type" in
        nvidia)
            configure_nvidia_gpu "$settings"
            ;;
        amd)
            configure_amd_gpu "$settings"
            ;;
        intel)
            configure_intel_gpu "$settings"
            ;;
        *)
            echo "Unknown GPU type: $gpu_type"
            return 1
            ;;
    esac
}

configure_nvidia_gpu() {
    local settings="$1"
    
    # Parse settings
    local power_limit=$(echo "$settings" | jq -r '.power_limit')
    local clock_offset=$(echo "$settings" | jq -r '.clock_offset')
    local memory_offset=$(echo "$settings" | jq -r '.memory_offset')
    local fan_speed=$(echo "$settings" | jq -r '.fan_speed')
    
    # Apply settings
    nvidia-smi -pm 1  # Enable persistent mode
    nvidia-smi -pl "$power_limit"  # Set power limit
    nvidia-settings -a "[gpu:0]/GPUGraphicsClockOffset[3]=$clock_offset"
    nvidia-settings -a "[gpu:0]/GPUMemoryTransferRateOffset[3]=$memory_offset"
    nvidia-settings -a "[gpu:0]/GPUFanControlState=1"
    nvidia-settings -a "[fan:0]/GPUTargetFanSpeed=$fan_speed"
}

configure_amd_gpu() {
    local settings="$1"
    
    # Parse settings
    local power_limit=$(echo "$settings" | jq -r '.power_limit')
    local clock_speed=$(echo "$settings" | jq -r '.clock_speed')
    local memory_speed=$(echo "$settings" | jq -r '.memory_speed')
    local fan_speed=$(echo "$settings" | jq -r '.fan_speed')
    
    # Apply settings using rocm-smi
    rocm-smi --setpoweroverdrive "$power_limit"
    rocm-smi --setsclk "$clock_speed"
    rocm-smi --setmclk "$memory_speed"
    rocm-smi --setfan "$fan_speed"
}

# Display management
manage_display() {
    local action="$1"
    local display="$2"
    shift 2
    
    case "$action" in
        configure)
            configure_display "$display" "$@"
            ;;
        optimize)
            optimize_display "$display" "$@"
            ;;
        reset)
            reset_display "$display"
            ;;
    esac
}

configure_display() {
    local display="$1"
    local mode="$2"
    local refresh_rate="$3"
    local position="${4:-0x0}"
    
    # Configure display using xrandr
    xrandr --output "$display" --mode "$mode" --rate "$refresh_rate" --pos "$position"
    
    # Apply gaming optimizations
    optimize_display_for_gaming "$display"
}

optimize_display_for_gaming() {
    local display="$1"
    
    # Enable gaming mode features
    xrandr --output "$display" --set "TearFree" "1"
    xrandr --output "$display" --set "FreeSync" "1"
    
    # Configure compositor
    if command -v picom &> /dev/null; then
        # Disable composition during fullscreen games
        picom --backend glx --unredir-if-possible
    fi
}

# Performance monitoring
monitor_gpu_performance() {
    local profile="$1"
    local duration="${2:-60}"
    
    echo "Monitoring GPU performance for profile: $profile"
    
    # Start monitoring
    {
        local end_time=$((SECONDS + duration))
        while [ $SECONDS -lt $end_time ]; do
            # Collect metrics
            local fps=$(get_current_fps)
            local temp=$(get_gpu_temperature)
            local power=$(get_gpu_power)
            local memory=$(get_gpu_memory)
            
            # Record metrics
            sqlite3 "${GAMING_DB}" << EOF
INSERT INTO gpu_performance (profile, fps, temperature, power_usage, memory_usage)
VALUES ('${profile}', ${fps}, ${temp}, ${power}, ${memory});
EOF
            
            sleep 1
        done
    } &
    
    # Wait for monitoring to complete
    wait
    
    # Generate performance report
    generate_gpu_report "$profile"
}

# Helper functions
get_gpu_temperature() {
    nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits || echo "0"
}

get_gpu_power() {
    nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits || echo "0"
}

get_gpu_memory() {
    nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits || echo "0"
}

# Report generation
generate_gpu_report() {
    local profile="$1"
    local report_file="${GAMING_ROOT}/reports/gpu_${profile}_$(date +%Y%m%d_%H%M%S).md"
    
    mkdir -p "${GAMING_ROOT}/reports"
    
    {
        echo "# GPU Performance Report"
        echo "Profile: $profile"
        echo "Generated: $(date)"
        echo
        
        echo "## Performance Metrics"
        sqlite3 "${GAMING_DB}" << EOF
SELECT
    round(avg(fps), 2) as avg_fps,
    round(avg(temperature), 2) as avg_temp,
    round(avg(power_usage), 2) as avg_power,
    round(avg(memory_usage), 2) as avg_memory
FROM gpu_performance
WHERE profile = '${profile}'
AND timestamp >= datetime('now', '-1 hour');
EOF
        
        echo
        echo "## GPU Configuration"
        echo "- Type: $(get_gpu_type)"
        echo "- Driver: $(get_gpu_driver_version)"
        echo "- Profile Settings:"
        get_gpu_profile_settings "$profile" | sed 's/^/  /'
        
    } > "$report_file"
    
    echo "GPU report generated: $report_file"
}

# Main functionality
main() {
    local command="$1"
    shift
    
    case "$command" in
        init)
            init_graphics_optimizer
            ;;
        optimize)
            optimize_driver "$@"
            ;;
        profile)
            manage_gpu_profile "$@"
            ;;
        configure)
            configure_gpu "$@"
            ;;
        display)
            manage_display "$@"
            ;;
        monitor)
            monitor_gpu_performance "$@"
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

