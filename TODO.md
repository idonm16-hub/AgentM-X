Planned next steps

- GUI skill (Windows):
  - Launch Notepad (pywinauto), type text, save to Desktop
  - Fallback to pyautogui if UIA fails
  - Basic OCR helper with pytesseract for validation

- Browser skill:
  - Playwright Chromium: open page, fill form, upload file, verify success

- Exec wrappers:
  - PowerShell/Win32/WMI/Tasks/Registry thin wrappers with logging

- API /run:
  - Start an AgentRunner execution and return run_id
  - Endpoint to query run status and fetch audit log

- Tests:
  - Add planner, registry expansion, self_improve cap test, basic e2e stubs
  - GUI/browser tests gated to Windows runners

- Config:
  - Support hardened mode toggle and approvals

- CI:
  - Windows GitHub Actions matrix job for GUI/Playwright
