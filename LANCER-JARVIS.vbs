' Lance Jarvis sans fenêtre noire, et ajoute l'icône Jarvis sur le Bureau si elle n'y est pas.
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
pyw = dir & "\.venv\Scripts\pythonw.exe"
If Not fso.FileExists(pyw) Then
  MsgBox "Jarvis n'est pas encore installé : double-clique d'abord sur INSTALLER-JARVIS.bat.", 48, "Jarvis"
  WScript.Quit
End If

lnk = shell.SpecialFolders("Desktop") & "\Jarvis.lnk"
If Not fso.FileExists(lnk) Then
  Set link = shell.CreateShortcut(lnk)
  link.TargetPath = pyw
  link.Arguments = "-m jarvis --fond"
  link.WorkingDirectory = dir
  ico = shell.ExpandEnvironmentStrings("%USERPROFILE%") & "\.jarvis\jarvis.ico"
  If fso.FileExists(ico) Then link.IconLocation = ico
  link.Description = "Jarvis, assistant personnel"
  link.Save
  MsgBox "Icône Jarvis ajoutée sur le Bureau.", 64, "Jarvis"
End If

shell.CurrentDirectory = dir
shell.Run """" & pyw & """ -m jarvis --fond", 0, False
