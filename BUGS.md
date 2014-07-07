 -*- mode: markdown; fill-column: 79; eval: (auto-fill-mode) -*-

 * On the first login on a TKL appliance, if the user's `TERM` variable is
   not in the terminfo database the `turnkey-init-fence` script will fail and
   all subsequent login attempts will fail. The workaround is to fix the `TERM`
   variable, wipe the screen session and login again:

		export TERM=<valid-terminal>
		ssh -t <appliance> screen -wipe
		ssh <appliance>
