Require conda
Source demos/_settings.tape
Output demos/configuration.gif
Output demos/.scratch/configuration.txt

Hide
Type@1ms "source demos/_prep.sh"
Enter
Wait /\$/
Ctrl+L
Sleep 500ms
Show

Type@80ms "# Inspect saved choices and effective values"
Enter
Type@80ms "conda feature config conda-completion --file .condarc --get"
Enter
Wait /\$/
Sleep 2s
Type@80ms "conda feature config conda-completion --file .condarc --show"
Enter
Wait /\$/
Sleep 3s
Ctrl+L
Type@80ms "# Save a shell choice without deploying a completion hook"
Enter
Type@80ms `conda feature config conda-completion --file .condarc \`
Enter
Type@80ms "  --set plugins.feature_completion_shell zsh --yes"
Enter
Wait /\$/
Sleep 3s
Type@80ms "conda feature config conda-completion --file .condarc --get"
Enter
Wait /\$/
Sleep 4s
Screenshot demos/.scratch/configuration.png
Sleep 500ms

Hide
Type@1ms "exit"
Enter
