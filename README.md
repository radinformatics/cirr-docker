# CIRR UP!

Derek Merck <derek_merck@brown.edu>
Rhode Island Hospital

Contributions from
Vanessa Sochat <vsochat@stanford.edu)
Stanford University School of Medicine

Configures and spins up a Docker-based open-source<sup><a name="^splunk_ref">[1](#^splunk)</a></sup> medical imaging informatics platform.  Originally developed to support the RIH Clinical Imaging Research Repository (CIRR).


## Services

- Clinical/PHI Facing Repository - [Orthanc] 1.0 on 4280 (HTTP/REST), 4242 (DICOM)
- Clinical/PHI Facing Receiver - Orthanc on 4380 (HTTP/REST), 4342 (DICOM)
- Research/Anonymized Facing Repository - [XNAT] 1.6.5 on 8080 (HTTP/REST), 8042 (DICOM)
- Database - [Postgresql] 9.5 on 3432 (SQL)
- Data Orchestration - _In progress_ [](Tithonus on 6080 (HTTP/REST))
- Log Monitoring - [Splunk] Lite on 1580 (HTTP/REST), 1514 (syslog)

[Splunk]:http://www.splunk.com
[Postgresql]:http://www.postgresql.org
[Orthanc]:http://www.orthanc-server.com
[XNAT]:http://www.xnat.org
[Tithonus]:https://github.com/derekmerck/Tithonus


## Dependencies

- [Docker], [docker-compose] for service virtualization
- [Python], [pyyaml], [jinja2] for `bootstrap.py`

[Docker]:http://www.docker.com
[docker-compose]:https://docs.docker.com/compose/
[Python]:http://www.python.org
[pyyaml]:http://pyyaml.org
[jinja2]:http://jinja.pocoo.org


## Configurations

Warning: once data has been ingested, _do not_ use `docker-compose down`, or you will drop the data volume!
Furthermore, _do not_ use `docker-compose up` with the xnat service; use `docker-compose up --no-recreate`  or it will fail because it can't rebuild itself if the database already exists.

`bootstrap.py` will read a file called `docker-compose.shadow.yml` and use any override variables or config information provided there.  All generated configuration files are similarly tagged as "shadow" and should not be indexed by `git` because they will contain plain-text account credentials.  Depending on which variables are used, `docker-compose.shadow.yml` may not be necessary to include when creating the containers themselves.


## Stanford Development
I (@vsoch) am using the simple Orthanc server (to start) located in [orthanc-docker](orthanc-docker). I've modified the code below to work with Python 3.5, however I'm starting with the simpler of these two versions. Complete instructions can be found in the [README](orthancp-docker/README.md)

This is an isolated Orthanc using a Postgres backend that can be created directly using `docker-compose` from the [orthancp-docker](orthancp-docker) directory.  This version has a much simpler configuration process, and by default it will create services on a separate network.


## Rhode Island Development

### Postgres

Orthanc and XNAT services rely on Postgres.  The Postgres service has to be available before Orthanc or XNAT can be configured.

```
$ docker-compose up -d postgres
```

### Orthanc w Postgres and Persistent Compressed Data Storage

First you want to set up orthanc.json from the template with the configuration from the running database. You can do this as follows:

```bash
$ python bootstrap.py orthanc
$ docker-compose up -d orthanc
```

Orthanc with receiver proxy:

```bash
$ python bootstrap.py orthanc orthanc-receiver
$ docker-compose up -d orthanc orthanc-reciever
```

The additional DICOM receiver can be used as a proxy to accept DICOM transfers and queue them for the main clinical-facing repository.  The main repo slows down considerably as the DB grows large, particularly if compression is on.<sup><a name="^timing_ref">[2](#^timing)</a></sup>


### XNAT w Postgres and Persistent Data Storage

```bash
$ python bootstrap.py xnat    # Initializes config from template, creates image, drops db if it exists
$ docker-compose up xnat
```

<!--
### XNAT and Orthanc with a Tithonus Gatekeeper

```bash
$ python bootstrap.py orthanc xnat
$ docker-compose up orthanc xnat tithonus
```

[Tithonus] can be configured to automatically move data from clinical DICOM sources into the clinical facing receiver, and from the clinical repository or other sources into the anonymized research-facing repository.
-->

### XNAT and Orthanc with a Splunk Log Handler

```
$ python bootstrap.py orthanc xnat
$ docker-compose up orthanc xnat splunk
```


### Complete CIRR Configuration

```bash
$ python bootstrap.py orthanc orthanc-receiver xnat
$ docker-compose up
```


### Administration

To inspect the data or logs, mount the data volumes on another container.

```
$ docker-compose up -f docker-compose.admin.yml admin
```

Or manually for a single service:

```bash
$ docker-compose run -it --volumes-from orthanc ubuntu /bin/bash
```

To perform a data backup, run `admin` or otherwise mount the volumes and use `tar`.

```bash
$ docker-compose run -f docker-compose.admin.yml admin tar zcvf /backup/postgres.tar.gz /var/lib/postgresql/data
$ docker-compose run -f docker-compose.admin.yml admin tar zcvf /backup/xnat.tar.gz /var/lib/xnat/data
```


## Acknowledgements

Uses Docker images from:

- [jodogne/orthanc](https://github.com/jodogne/OrthancDocker)
- [chaseglove/xnat](https://github.com/chaselgrove/xnat-docker)
- [outcoldman/splunk](https://github.com/outcoldman/docker-splunk)


## Note

Run this command to configure your shell to use `docker-compose` on OSX or Windows:

```
$ eval "$(docker-machine env default)"
```

## License

MIT

---

<a name="^splunk">1</a>: Splunk is not open source, but Splunk Lite will work for this volume of logs and it _is_ free.  Replace it with you open-source syslog server of choice if necessary.[:arrow_heading_up:](#^splunk_ref)

<a name="^timing">2</a>: On a reasonable machine, we measured about 20 images/second in an empty, uncompressed repo, but only about 1.5 scans/sec in a repo w 100k instances and compression on.[:arrow_heading_up:](#^timing_ref)
