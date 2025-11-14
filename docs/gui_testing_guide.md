# GUI Manual Testing Guide

## Overview

This guide provides comprehensive test cases for manually testing the Modem Inspector GUI application. Follow these test scenarios to verify all functionality works correctly.

## Prerequisites

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Hardware Setup**
   - USB modem or serial device (optional for full testing)
   - USB cable
   - Serial port available on your system

3. **Launch GUI**
   ```bash
   py main.py
   # or
   py main.py --gui
   ```

---

## Test Scenarios

### 1. Application Startup

**Test Case 1.1: GUI Launches Successfully**
- **Steps:**
  1. Run `py main.py`
  2. Observe application window opens
- **Expected:**
  - Window titled "Modem Inspector - GUI" appears
  - Window size is 1200x800
  - No error messages in console
  - Menu bar visible (File, Settings, Help)
  - All frames visible: Connection, Plugin, Execution & Results, Command Categories, Communication Logs

**Test Case 1.2: Plugin Discovery on Startup**
- **Steps:**
  1. Launch GUI
  2. Check console output
- **Expected:**
  - Console shows "Discovered X plugins" message
  - No plugin discovery errors

**Test Case 1.3: History Loading**
- **Steps:**
  1. Launch GUI (after previous inspections)
  2. Check console output
- **Expected:**
  - Console shows "Loaded X recent inspections" if history exists
  - No errors loading history

---

### 2. Menu Bar Testing

**Test Case 2.1: File Menu**
- **Steps:**
  1. Click "File" in menu bar
  2. Click "Exit"
- **Expected:**
  - Application closes gracefully
  - No error messages
  - Serial ports closed if connected

**Test Case 2.2: Settings Menu**
- **Steps:**
  1. Click "Settings" in menu bar
- **Expected:**
  - Settings dialog opens
  - Dialog is modal (blocks main window)
  - Dialog centered on main window

**Test Case 2.3: Help Menu**
- **Steps:**
  1. Click "Help" → "Help"
  2. Close help dialog
  3. Click "Help" → "About"
- **Expected:**
  - Help dialog opens with searchable content
  - About dialog shows version and copyright info
  - Both dialogs are modal

---

### 3. Connection Frame Testing

**Test Case 3.1: Port Discovery**
- **Steps:**
  1. Click "Refresh" button in Connection frame
  2. Observe port dropdown
- **Expected:**
  - Dropdown populates with available ports
  - Each port shows description (e.g., "COM3 - USB Serial Port")
  - If no ports: shows message "No ports found"

**Test Case 3.2: Connection Success**
- **Steps:**
  1. Select a port from dropdown
  2. Click "Connect" button
  3. Observe status indicator
- **Expected:**
  - Status indicator turns green
  - "Connect" button changes to "Disconnect"
  - Port dropdown disabled
  - Console shows "Port opened successfully" (if verbose)
  - Plugin auto-detect button becomes enabled

**Test Case 3.3: Connection Failure**
- **Steps:**
  1. Select invalid port (e.g., manually type "COM99")
  2. Click "Connect"
- **Expected:**
  - Error dialog appears with clear message
  - Status indicator stays gray/red
  - "Connect" button remains enabled
  - Port dropdown remains enabled

**Test Case 3.4: Disconnect**
- **Steps:**
  1. Connect to a port
  2. Click "Disconnect" button
- **Expected:**
  - Status indicator turns gray
  - "Disconnect" button changes to "Connect"
  - Port dropdown re-enabled
  - Communication logs stop updating

---

### 4. Plugin Frame Testing

**Test Case 4.1: Auto-Detection**
- **Prerequisites:** Connected to modem
- **Steps:**
  1. Click "Auto-Detect" button
  2. Wait for detection to complete
- **Expected:**
  - Button shows "Detecting..." during process
  - Progress indicator or spinner visible
  - Plugin selected automatically in dropdown
  - Plugin info displayed (vendor, model, version, command count)
  - Command categories populated in "Command Categories" tab

**Test Case 4.2: Manual Selection**
- **Steps:**
  1. Click plugin dropdown
  2. Select a plugin manually
- **Expected:**
  - Plugin info updates
  - Command categories populate
  - Command count displays
  - Execution frame becomes ready

**Test Case 4.3: Plugin Info Display**
- **Steps:**
  1. Select a plugin
  2. Observe plugin info section
- **Expected:**
  - Vendor name displayed
  - Model name displayed
  - Plugin version displayed
  - Total command count displayed
  - All fields properly formatted

**Test Case 4.4: Search Plugin**
- **Steps:**
  1. Click plugin dropdown
  2. Type part of plugin name
- **Expected:**
  - Dropdown filters to matching plugins
  - Search is case-insensitive

---

### 5. Command Categories Testing

**Test Case 5.1: Category Display**
- **Prerequisites:** Plugin selected
- **Steps:**
  1. Navigate to "Command Categories" tab
  2. Observe category list
- **Expected:**
  - All categories from plugin displayed
  - Each category shows command count
  - Checkboxes for each category
  - "Select All" and "Deselect All" buttons visible
  - "Quick Scan Only" checkbox visible

**Test Case 5.2: Select/Deselect Categories**
- **Steps:**
  1. Check/uncheck individual categories
  2. Observe command count update
- **Expected:**
  - Command count updates dynamically
  - Execution frame updates with selected commands
  - At least one category must be selected to execute

**Test Case 5.3: Select All / Deselect All**
- **Steps:**
  1. Click "Select All"
  2. Click "Deselect All"
- **Expected:**
  - "Select All" checks all categories
  - "Deselect All" unchecks all categories
  - Command count updates accordingly

**Test Case 5.4: Quick Scan Filter**
- **Steps:**
  1. Check "Quick Scan Only"
  2. Observe command count
- **Expected:**
  - Command count shows only "quick" commands
  - Non-quick commands filtered out
  - Execution uses filtered list

---

### 6. Execution Frame Testing

**Test Case 6.1: Execution Ready State**
- **Prerequisites:** Connected and plugin selected
- **Steps:**
  1. Select categories
  2. Observe "Start" button
- **Expected:**
  - "Start" button enabled
  - Command count displays (e.g., "0 / 15 commands")
  - Progress bar at 0%

**Test Case 6.2: Command Execution**
- **Prerequisites:** Ready to execute
- **Steps:**
  1. Click "Start" button
  2. Observe execution progress
- **Expected:**
  - "Start" button changes to "Cancel"
  - Progress bar updates in real-time
  - Progress log shows commands being executed
  - Elapsed time updates
  - Estimated time remaining displays
  - Command count increments (e.g., "5 / 15 commands")

**Test Case 6.3: Progress Log Color Coding**
- **Steps:**
  1. Execute commands
  2. Observe log entries
- **Expected:**
  - Success: Green text (e.g., "✓ AT+CGMI: OK")
  - Error: Red text (e.g., "✗ AT+INVALID: ERROR")
  - Retry: Yellow text (e.g., "⟳ AT+CGMM: Retry 1/3")
  - Auto-scrolls to bottom

**Test Case 6.4: Cancel Execution**
- **Steps:**
  1. Start execution
  2. Click "Cancel" button mid-execution
- **Expected:**
  - Execution stops gracefully
  - "Cancel" button changes back to "Start"
  - Progress log shows "Execution cancelled by user"
  - Partial results available in Results frame

**Test Case 6.5: Execution Complete**
- **Steps:**
  1. Complete full execution
  2. Observe final state
- **Expected:**
  - Progress bar at 100%
  - "Cancel" button changes to "Start"
  - Execution summary displays (e.g., "Completed: 15/15 commands (13 success, 2 errors)")
  - Results populate in Results frame

---

### 7. Results Frame Testing

**Test Case 7.1: Results Display**
- **Prerequisites:** Execution completed
- **Steps:**
  1. Navigate to "Execution & Results" tab
  2. Observe Results panel
- **Expected:**
  - Results organized by category tabs
  - Each result shows: command, status, timing, response
  - Success results in green
  - Error results in red

**Test Case 7.2: Search Functionality**
- **Steps:**
  1. Enter search term in search box
  2. Observe results
- **Expected:**
  - Matching results highlighted
  - Case-insensitive search
  - Searches command, status, and response text

**Test Case 7.3: Copy to Clipboard**
- **Steps:**
  1. Click "Copy to Clipboard" button
  2. Paste into text editor
- **Expected:**
  - All results copied in formatted text
  - Includes commands, statuses, responses
  - Properly formatted and readable

**Test Case 7.4: Export Button**
- **Steps:**
  1. Click "Export" button
- **Expected:**
  - Report dialog opens
  - All results passed to dialog

**Test Case 7.5: Pagination (100+ Commands)**
- **Prerequisites:** Plugin with 100+ commands
- **Steps:**
  1. Execute all commands
  2. Observe results display
- **Expected:**
  - Pagination controls visible
  - Shows 20 results per page
  - "Next" and "Previous" buttons work
  - Page indicator shows current page (e.g., "Page 1 of 6")

---

### 8. Communication Logs Testing

**Test Case 8.1: Log Display**
- **Prerequisites:** Logging enabled in settings, connected
- **Steps:**
  1. Navigate to "Communication Logs" tab
  2. Execute some commands
- **Expected:**
  - Real-time log entries appear
  - Shows sent commands and received responses
  - Timestamps displayed
  - Auto-scrolls to bottom

**Test Case 8.2: Log Filtering**
- **Steps:**
  1. Enter filter text in log search box
  2. Observe filtered logs
- **Expected:**
  - Only matching entries shown
  - Filter is case-insensitive
  - Clear filter restores all entries

**Test Case 8.3: Clear Logs**
- **Steps:**
  1. Click "Clear Logs" button
- **Expected:**
  - All log entries cleared from display
  - File logs preserved (only display cleared)

---

### 9. Settings Dialog Testing

**Test Case 9.1: Open Settings**
- **Steps:**
  1. Click "Settings" in menu
  2. Observe dialog
- **Expected:**
  - Modal dialog opens
  - Three tabs visible: Serial, Reports, Logging
  - Current settings loaded and displayed

**Test Case 9.2: Serial Settings Tab**
- **Steps:**
  1. Navigate to Serial tab
  2. Modify baud rate, timeout, retry attempts, retry delay
  3. Click "Save"
- **Expected:**
  - All fields editable
  - Validation on save (invalid values rejected with error)
  - Dialog closes on successful save

**Test Case 9.3: Reports Settings Tab**
- **Steps:**
  1. Navigate to Reports tab
  2. Click "Browse" button
  3. Select directory
  4. Click "Save"
- **Expected:**
  - File dialog opens
  - Selected directory displays in text field
  - Path validated on save

**Test Case 9.4: Logging Settings Tab**
- **Steps:**
  1. Navigate to Logging tab
  2. Check "Enable Communication Logging"
  3. Configure log options
  4. Click "Save"
- **Expected:**
  - Enabling logging enables related controls
  - Log level dropdown functional
  - "Log to File" and "Log to Console" checkboxes work
  - "Browse" button opens file dialog
  - "Open Log Directory" button opens directory in file explorer

**Test Case 9.5: Reset to Defaults**
- **Steps:**
  1. Modify some settings
  2. Click "Reset to Defaults"
  3. Confirm in dialog
- **Expected:**
  - Confirmation dialog appears
  - On confirm: all settings reset to defaults
  - Success message displays
  - Settings reloaded in UI

**Test Case 9.6: Validation Errors**
- **Steps:**
  1. Enter invalid baud rate (e.g., "abc" or "999999")
  2. Click "Save"
- **Expected:**
  - Error dialog displays specific error
  - Switches to offending tab
  - Highlights/focuses invalid field
  - Dialog remains open

**Test Case 9.7: Cancel Settings**
- **Steps:**
  1. Modify settings
  2. Click "Cancel"
- **Expected:**
  - Dialog closes without saving
  - Settings unchanged

---

### 10. Report Dialog Testing

**Test Case 10.1: Open Report Dialog**
- **Prerequisites:** Execution results available
- **Steps:**
  1. Click "Export" button in Results frame
- **Expected:**
  - Report dialog opens
  - Shows count of commands to export
  - Default filename with timestamp suggested
  - Format dropdown shows CSV (default), HTML, JSON, Markdown

**Test Case 10.2: Format Selection**
- **Steps:**
  1. Select different formats from dropdown
- **Expected:**
  - Format changes reflect in file extension
  - Options checkboxes remain functional
  - Note: Only CSV fully implemented

**Test Case 10.3: Format Options**
- **Steps:**
  1. Check/uncheck "Include raw responses"
  2. Check/uncheck "Include timestamps"
- **Expected:**
  - Checkboxes toggle independently
  - Default: both checked

**Test Case 10.4: Browse Output Path**
- **Steps:**
  1. Click "Browse" button
  2. Select location and filename
- **Expected:**
  - File save dialog opens
  - Selected path populates in text field
  - Default filename includes timestamp

**Test Case 10.5: Generate Report**
- **Steps:**
  1. Configure format and options
  2. Select output path
  3. Click "Generate" button
- **Expected:**
  - Button changes to "Generating..."
  - Progress bar appears and animates
  - Generation happens in background (UI responsive)
  - Success message shows file size and path
  - "Open Report" button becomes enabled

**Test Case 10.6: File Overwrite Confirmation**
- **Steps:**
  1. Select existing file path
  2. Click "Generate"
- **Expected:**
  - Confirmation dialog appears
  - On confirm: file overwritten
  - On cancel: generation cancelled

**Test Case 10.7: Open Report**
- **Steps:**
  1. Generate report successfully
  2. Click "Open Report" button
- **Expected:**
  - Report opens in default application (Excel for CSV)
  - Works on Windows, macOS, and Linux

**Test Case 10.8: Generation Error**
- **Steps:**
  1. Select read-only directory
  2. Click "Generate"
- **Expected:**
  - Error message displays
  - Describes the error clearly
  - Dialog remains open for correction

---

### 11. Error Handling Testing

**Test Case 11.1: Serial Port Errors**
- **Steps:**
  1. Connect to port
  2. Physically disconnect device
  3. Try to execute commands
- **Expected:**
  - Error dialog with clear message
  - Graceful recovery (can reconnect)
  - No application crash

**Test Case 11.2: Timeout Errors**
- **Steps:**
  1. Set very short timeout (1 second)
  2. Execute slow commands
- **Expected:**
  - Commands timeout gracefully
  - Timeout status shown in results
  - Execution continues with next command

**Test Case 11.3: Invalid AT Commands**
- **Steps:**
  1. Execute plugin with invalid commands
- **Expected:**
  - Error status shown in results
  - Error details in response
  - No application crash

---

### 12. Resource Cleanup Testing

**Test Case 12.1: Normal Exit**
- **Steps:**
  1. Connect to port
  2. Start logging
  3. Execute commands
  4. Close application via File → Exit
- **Expected:**
  - Serial port closed
  - Log files flushed and closed
  - No error messages
  - Clean shutdown

**Test Case 12.2: Window Close Button**
- **Steps:**
  1. Connect and execute
  2. Click window close button (X)
- **Expected:**
  - Same cleanup as Test Case 12.1
  - Resources released properly

---

## Test Results Template

Use this template to record test results:

```
Test Date: _______________
Tester: _______________
OS: _______________
Python Version: _______________

| Test Case | Status | Notes |
|-----------|--------|-------|
| 1.1 | PASS/FAIL | |
| 1.2 | PASS/FAIL | |
| ... | ... | ... |

Overall Assessment: _______________
Critical Issues: _______________
Minor Issues: _______________
```

---

## Known Limitations

1. **HTML/JSON/Markdown Reports**: Only CSV fully implemented
2. **Advanced Settings Tab**: Placeholder - configure via config.yaml
3. **Recent History Display**: Loads but not displayed in UI (console only)

---

## Troubleshooting

### GUI Won't Launch
- **Error:** `ImportError: customtkinter`
  - **Solution:** `pip install customtkinter pillow`

### Port Not Detected
- **Error:** "No ports found"
  - **Solution:**
    - Check USB cable connected
    - Check device drivers installed
    - Try `py main.py --cli --discover-ports`

### Execution Freezes
- **Symptom:** UI unresponsive during execution
  - **Issue:** Threading problem
  - **Workaround:** Restart application

### Log Files Not Created
- **Check:** Settings → Logging tab
  - Ensure "Enable Communication Logging" checked
  - Ensure "Log to File" checked
  - Check log directory permissions

---

## Reporting Issues

When reporting issues, please include:
1. Test case number
2. OS and Python version
3. Steps to reproduce
4. Expected vs. actual behavior
5. Screenshots (if applicable)
6. Error messages from console
7. Log files (if available)

Submit issues to: https://github.com/modem-inspector/modem-inspector/issues
