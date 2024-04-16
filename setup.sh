#! /bin/sh

sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo groupadd docker
sudo usermod -aG docker cjean

# queue
mkfifo shared/host_executor_queue

#( (crontab -l 2>/dev/null || true; cat my-cron-jobs.txt) | sort -u) | crontab -

#@reboot tail -f host_executor_queue | sh &

# https://stackoverflow.com/questions/32163955/how-to-run-shell-script-on-host-from-docker-container
# Make a named pipe using 'mkfifo host_executor_queue' where the volume is mounted. Then to add a consumer which executes commands that are put into the queue as host's shell, use 'tail -f host_executor_queue | sh &'. The & at the end makes it run in the background. Finally to push commands into the queue use 'echo touch foo > host_executor_queue' - this test creates a temp file foo at home directory. If you want the consumer to start at system startup, put '@reboot tail -f host_executor_queue | sh &' in crontab. Just add relative path to host_executor_queue.