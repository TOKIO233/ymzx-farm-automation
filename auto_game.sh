#!/system/bin/sh
# 元梦之星农场自动化脚本 - 简化版

# ==================== 配置参数 ====================
CONFIG_FILE="/data/data/com.termux/files/home/ymzx/config_commands.txt"

# 时间间隔参数 (单位: 秒)
DEFAULT_INTERVAL=0.8    # 命令之间的默认间隔 (800ms)
KEY_INTERVAL=0.8        # 按键之间的间隔 (800ms)
SEQ_INTERVAL=2.0        # 命令序列之间的间隔 (2000ms)

# ==================== 核心函数 ====================

# 日志函数
log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

# 检查是否为数字
is_num() {
    case "$1" in
        ''|*[!0-9]*) return 1 ;;
        *) return 0 ;;
    esac
}

# 执行单个命令
do_cmd() {
    local cmd="$1"
    
    log "执行命令: $cmd"
    
    # 时间间隔命令 (xxxms)
    if echo "$cmd" | grep -q "ms$"; then
        local delay=$(echo "$cmd" | sed 's/ms$//')
        if is_num "$delay"; then
            log "等待 ${delay}ms"
            sleep $(echo "scale=3; $delay / 1000" | bc 2>/dev/null || echo "1")
            return 0
        else
            log "ERROR: 无效时间格式 $cmd"
            return 1
        fi
    fi
    
    # 滑动命令 (SWIPE:x1,y1,x2,y2,duration)
    if echo "$cmd" | grep -q "^SWIPE:"; then
        local params=$(echo "$cmd" | cut -d: -f2)
        local x1=$(echo "$params" | cut -d, -f1)
        local y1=$(echo "$params" | cut -d, -f2)
        local x2=$(echo "$params" | cut -d, -f3)
        local y2=$(echo "$params" | cut -d, -f4)
        local dur=$(echo "$params" | cut -d, -f5)
        
        if is_num "$x1" && is_num "$y1" && is_num "$x2" && is_num "$y2" && is_num "$dur"; then
            log "滑动: ($x1,$y1) → ($x2,$y2) ${dur}ms"
            input swipe $x1 $y1 $x2 $y2 $dur
            return 0
        else
            log "ERROR: 滑动参数错误 $cmd"
            return 1
        fi
    fi
    
    # 点击命令 (x,y)
    if echo "$cmd" | grep -q "^[0-9]*,[0-9]*$"; then
        local x=$(echo "$cmd" | cut -d, -f1)
        local y=$(echo "$cmd" | cut -d, -f2)
        
        if is_num "$x" && is_num "$y"; then
            log "点击: ($x,$y)"
            input tap $x $y
            return 0
        else
            log "ERROR: 点击坐标错误 $cmd"
            return 1
        fi
    fi
    
    # 移动命令 (W3, A2, S1, D4)
    if echo "$cmd" | grep -q "^[WwAaSsDd][0-9]*$"; then
        local dir=$(echo "$cmd" | cut -c1 | tr '[:lower:]' '[:upper:]')
        local num=$(echo "$cmd" | cut -c2-)
        
        if ! is_num "$num" || [ "$num" -le 0 ]; then
            log "ERROR: 移动次数错误 $cmd"
            return 1
        fi
        
        # 键位映射
        local keycode=""
        case "$dir" in
            W) keycode=51 ;;  # 上
            A) keycode=29 ;;  # 左
            S) keycode=47 ;;  # 下
            D) keycode=32 ;;  # 右
            *) 
                log "ERROR: 无效方向 $dir"
                return 1
                ;;
        esac
        
        log "移动: $dir 方向 $num 次"
        local i=1
        while [ $i -le $num ]; do
            input keyevent --longpress $keycode
            if [ $i -lt $num ]; then
                sleep $KEY_INTERVAL
            fi
            i=$((i + 1))
        done
        return 0
    fi
    
    log "ERROR: 无法识别命令 $cmd"
    return 1
}

# 执行命令行
run_line() {
    local line="$1"

    if [ -z "$line" ]; then
        log "WARNING: 命令行为空，跳过"
        return 0
    fi

    log "执行命令行: $line"

    # 先计算命令总数
    local cmd_count=0
    for cmd in $line; do
        cmd_count=$((cmd_count + 1))
    done

    log "共 $cmd_count 个命令"

    # 执行每个命令
    local current_cmd=0
    for cmd in $line; do
        current_cmd=$((current_cmd + 1))

        if ! do_cmd "$cmd"; then
            log "ERROR: 命令执行失败，停止执行"
            return 1
        fi

        # 添加默认间隔（除了最后一个命令）
        if [ $current_cmd -lt $cmd_count ]; then
            log "默认间隔 ${DEFAULT_INTERVAL}s"
            sleep $DEFAULT_INTERVAL
        fi
    done

    log "命令行执行完成"
    return 0
}

# 执行所有命令行
run_all_lines() {
    if [ ! -f "$CONFIG_FILE" ]; then
        log "ERROR: 配置文件不存在 $CONFIG_FILE"
        exit 1
    fi

    log "读取配置文件: $CONFIG_FILE, 执行所有命令行"

    # 先计算总的有效行数
    local total_valid=0
    while IFS= read -r line || [ -n "$line" ]; do
        # 跳过注释和空行
        if echo "$line" | grep -q "^#" || [ -z "$line" ]; then
            continue
        fi
        total_valid=$((total_valid + 1))
    done < "$CONFIG_FILE"

    log "共找到 $total_valid 行有效命令"

    # 执行所有有效行
    local current=0
    local valid=0

    while IFS= read -r line || [ -n "$line" ]; do
        current=$((current + 1))

        # 跳过注释和空行
        if echo "$line" | grep -q "^#" || [ -z "$line" ]; then
            continue
        fi

        valid=$((valid + 1))

        log "=== 执行第 $valid/$total_valid 行命令 (文件第 $current 行) ==="
        log "命令内容: $line"

        # 执行这一行命令序列
        if ! run_line "$line"; then
            log "ERROR: 第 $valid 行命令序列执行失败"
            exit 1
        fi

        log "第 $valid 行命令序列执行完成"

        # 行间间隔（除了最后一行）
        if [ $valid -lt $total_valid ]; then
            log "行间间隔 ${SEQ_INTERVAL}s"
            sleep $SEQ_INTERVAL
        fi

    done < "$CONFIG_FILE"

    log "所有命令行执行完成！共执行 $valid 行命令"
    return 0
}

# 执行指定行
run_single_line() {
    local line_num="$1"

    if [ ! -f "$CONFIG_FILE" ]; then
        log "ERROR: 配置文件不存在 $CONFIG_FILE"
        exit 1
    fi

    log "读取配置文件: $CONFIG_FILE, 执行第 $line_num 行"

    local current=0
    local valid=0

    while IFS= read -r line || [ -n "$line" ]; do
        current=$((current + 1))

        # 跳过注释和空行
        if echo "$line" | grep -q "^#" || [ -z "$line" ]; then
            continue
        fi

        valid=$((valid + 1))

        if [ $valid -eq $line_num ]; then
            log "找到第 $line_num 行 (文件第 $current 行): $line"

            # 直接执行这一行命令序列
            if ! run_line "$line"; then
                log "ERROR: 命令序列执行失败"
                exit 1
            fi

            log "命令序列执行完成"
            exit 0
        fi
    done < "$CONFIG_FILE"

    log "ERROR: 未找到第 $line_num 行命令 (共 $valid 行有效命令)"
    exit 1
}

# 主函数
main() {
    local line_num="$1"

    # 如果没有指定行号，执行所有行
    if [ -z "$line_num" ]; then
        run_all_lines
    else
        run_single_line "$line_num"
    fi
}

# 显示配置
show_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        log "ERROR: 配置文件不存在 $CONFIG_FILE"
        exit 1
    fi

    echo "=== 配置参数 ==="
    echo "默认间隔: ${DEFAULT_INTERVAL}s"
    echo "按键间隔: ${KEY_INTERVAL}s"
    echo "序列间隔: ${SEQ_INTERVAL}s"
    echo "配置文件: $CONFIG_FILE"
    echo ""

    echo "=== 配置文件内容 ==="
    local line_num=0
    local valid=0

    while IFS= read -r line || [ -n "$line" ]; do
        line_num=$((line_num + 1))

        if echo "$line" | grep -q "^#" || [ -z "$line" ]; then
            echo "    $line"
            continue
        fi

        valid=$((valid + 1))

        # 计算命令数量
        local cmd_count=0
        for cmd in $line; do
            cmd_count=$((cmd_count + 1))
        done

        echo "[$valid] 包含 $cmd_count 个命令"
        echo "    $line"
        echo ""
    done < "$CONFIG_FILE"

    echo "=== 共 $valid 行有效命令 ==="
}

# 解析参数
case "$1" in
    -c|--config)
        show_config
        ;;
    -h|--help)
        echo "使用方法: sh auto_game.sh [行号|选项]"
        echo "选项:"
        echo "  -c, --config    显示配置文件内容"
        echo "  -h, --help      显示此帮助信息"
        echo "参数:"
        echo "  行号            执行配置文件中指定行的命令"
        echo "  无参数          执行所有有效命令行 (默认行为)"
        ;;
    *)
        if [ -z "$1" ]; then
            main
        elif is_num "$1" && [ "$1" -gt 0 ]; then
            main "$1"
        else
            log "ERROR: 无效参数 $1"
            echo "使用 -h 查看帮助"
            exit 1
        fi
        ;;
esac
