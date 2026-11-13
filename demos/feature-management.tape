Require conda
Source demos/_settings.tape
Output demos/feature-management.gif
Output demos/.scratch/feature-management.txt

Hide
Type@1ms "source demos/_prep.sh"
Enter
Wait /\$/
Ctrl+L
Sleep 500ms
Show

Type@80ms "conda feature list"
Enter
Wait /\$/
Sleep 3s
Screenshot demos/.scratch/list.png
Sleep 500ms
Ctrl+L
Type@80ms "conda feature explain conda-pypi"
Enter
Wait /\$/
Sleep 5s
Screenshot demos/.scratch/explain.png
Sleep 500ms
Ctrl+L
Type@80ms "conda feature enable conda-pypi --file .condarc --dry-run"
Enter
Wait /\$/
Sleep 4s
Screenshot demos/.scratch/preview.png
Sleep 500ms
Ctrl+L
Type@80ms "conda feature enable conda-pypi --file .condarc --yes"
Enter
Wait /\$/
Sleep 4s
Screenshot demos/.scratch/enable.png
Sleep 500ms
Ctrl+L
Type@80ms "conda feature disable conda-pypi --file .condarc --yes"
Enter
Wait /\$/
Sleep 4s
Screenshot demos/.scratch/disable.png
Sleep 500ms

Hide
Type@1ms "exit"
Enter
