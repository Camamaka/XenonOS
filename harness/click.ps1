param([string]$Title, [int]$X, [int]$Y, [int]$Count = 1, [int]$GapMs = 90)
Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class WinClick {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll")] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  public static IntPtr Find(string needle) {
    IntPtr found = IntPtr.Zero;
    EnumWindows((h, l) => {
      if (found != IntPtr.Zero || !IsWindowVisible(h)) return true;
      var sb = new StringBuilder(256); GetWindowText(h, sb, 256);
      if (sb.ToString().IndexOf(needle, StringComparison.OrdinalIgnoreCase) >= 0) found = h;
      return true;
    }, IntPtr.Zero);
    return found;
  }
}
"@
$h = [WinClick]::Find($Title)
if ($h -eq [IntPtr]::Zero) { "no window: $Title"; exit 1 }
[void][WinClick]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 600
$r = New-Object WinClick+RECT
[void][WinClick]::GetWindowRect($h, [ref]$r)
$sx = $r.L + $X; $sy = $r.T + $Y
[void][WinClick]::SetCursorPos($sx, $sy)
Start-Sleep -Milliseconds 250
for ($i = 0; $i -lt $Count; $i++) {
  [WinClick]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)   # left button down
  [WinClick]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)   # left button up
  Start-Sleep -Milliseconds $GapMs
}
"tiklandi: ekran ($sx,$sy) x$Count"
