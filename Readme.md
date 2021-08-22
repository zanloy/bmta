# BIP Mail Transfer Agent

## Summary
The point of this application is to act as a single point relay for all mail from inside the environment and filter out IP addresses from emails.

## Quickstart
To run this app on your desktop (as long as it can run Docker) is to use the following command:

```sh
$ docker run --rm -it -p 2525:2525 --name bmta zanloy/bmta:1.0
```

Notes:
* This will not work from your GFE because connections to the upstream SMTP server on port 25 is blocked. It only works from the GovCloud AWS environment.
* You can change the port by modifying `-p 2525:2525` to something else like `-p 2525:25` (to bind to port 25, you will need to be root).

## Install into Kubernetes via Helm Chart

This is still a work-in-progress.