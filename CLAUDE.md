# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Yuan Meng Zhi Xing (元梦之星) farm automation project that uses ADB commands to simulate WASD key operations for precise character movement control. The project supports both PC debugging mode and direct mobile execution.

## Core Architecture

The project consists of two main execution modes:

### PC Debugging Mode (`move_debugger.py`)
- **Purpose**: Development, testing, and parameter calibration
- **Features**: Interactive menu system with 7 main functions including movement testing, distance calibration, unified command execution, and touch parameter recording
- **Environment**: Requires Python 3.6+, ADB tools, and Android device with USB debugging

### Mobile Direct Execution (`auto_game.sh`)
- **Purpose**: Production automation scripts running directly on mobile devices
- **Features**: Configuration file management, batch command execution, and parameter consistency with PC version
- **Environment**: Android 4.0+, requires either Root permissions or Shizuku + automation software

## Command Development Guidelines

### Building and Testing
```bash
# PC mode - Run main debugger
python move_debugger.py

# Mobile mode - View configuration
sh auto_game.sh -c

# Mobile mode - Execute all commands (default)
sh auto_game.sh

# Mobile mode - Execute specific line (1-9)
sh auto_game.sh 1
```

### Core Command Types

The system supports unified command syntax with three types:
1. **Movement Commands**: `W3 A2 S1 D4` (direction + count)
2. **Click Commands**: `540,960` (x,y coordinates)  
3. **Swipe Commands**: `SWIPE:x1,y1,x2,y2,duration` (start, end, duration in ms)
4. **Timing Commands**: `1000ms` (wait time)

### Key System Parameters

**Critical timing parameters (must be consistent across both files):**
```python
DEFAULT_INTERVAL = 0.8    # Command interval (800ms)
KEY_INTERVAL = 0.8        # Key press interval (800ms)  
SEQ_INTERVAL = 2.0        # Sequence interval (2000ms)
```

**Key mappings (Android keycodes):**
```python
KEYCODE_W = "51"  # Up movement
KEYCODE_A = "29"  # Left movement
KEYCODE_S = "47"  # Down movement
KEYCODE_D = "32"  # Right movement
```

## Project Structure

### Core Files
- `move_debugger.py` - PC debugging script with interactive menu system
- `auto_game.sh` - Mobile execution script with configuration management
- `config_commands.txt` - Command configuration file storing preset operation sequences
- `README.md` - Comprehensive documentation

### Generated Files
- `move_debugger.log` - Detailed operation logs (PC)
- `movement_calibration.txt` - Movement distance calibration data (PC)
- `touch_commands.txt` - Touch parameter recordings with command generation
- `touch_commands.json` - JSON format touch recordings

## Architecture Patterns

### Parameter Consistency System
Both `move_debugger.py` and `auto_game.sh` maintain identical:
- Key mappings (W=51, A=29, S=47, D=32)
- Execution methods (`input keyevent --longpress`)
- Timing intervals (DEFAULT_INTERVAL, KEY_INTERVAL, SEQ_INTERVAL)

### Touch Event Recording System
Advanced touch parameter recording system in `move_debugger.py`:
- Uses `adb shell getevent` for real-time touch monitoring
- Intelligent click/swipe distinction based on movement distance
- Automatic coordinate transformation from touch sensor to screen coordinates
- Dual output format (text and JSON) for different use cases

### Configuration Management
- Comment support in config files (lines starting with #)
- Line-by-line command execution with automatic sequence management
- Mixed command support within single sequences
- Batch processing with configurable intervals

## Development Workflow

1. **PC Development**: Use `move_debugger.py` for testing and parameter tuning
2. **Distance Calibration**: Use menu option 2 to establish key-press to movement relationships
3. **Touch Recording**: Use menu option 7 to record complex touch sequences
4. **Mobile Deployment**: Transfer scripts and configs to mobile device
5. **Production Execution**: Use `auto_game.sh` for automated farming sequences

## Critical Implementation Details

### Why longpress Method
Regular keyevent commands don't register with the game - only `--longpress` method is recognized as valid input by Yuan Meng Zhi Xing.

### Coordinate System
- Screen coordinates vary by device resolution
- Touch sensor coordinates require transformation to screen coordinates
- Calibration recommended for different devices using built-in screen info tools

### Error Handling
- Comprehensive ADB connection monitoring
- Timeout protection for all external commands
- Detailed logging for troubleshooting
- Parameter validation before execution

## Mobile Deployment Options

**Method 1: Termux + Root** (Traditional, tested)
- Install Termux, obtain root permissions
- Transfer scripts, set execute permissions
- Direct shell execution

**Method 2: Shizuku + Automation** (Root-free, experimental)
- Install Shizuku, activate via ADB
- Use automation software with Shizuku permissions
- Configure shell command tasks

This project demonstrates sophisticated Android automation with dual-mode architecture, ensuring consistency between development and production environments while providing comprehensive tooling for complex touch sequence automation.