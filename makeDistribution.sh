
# take the current version of the repos and place it on the distribution server
# for the Pis to download from.
rsync -avzhe ssh dist pi@grayling.sics.se:dist
