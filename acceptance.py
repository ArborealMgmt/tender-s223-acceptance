#!/usr/bin/env python3
"""Real acceptance assertions; failures produce failing JUnit and nonzero exit."""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", action="store_true")
    args = parser.parse_args()
    suite = ET.Element("testsuite", name="s223-acceptance")
    failures = 0

    def check(name, action):
        nonlocal failures
        case = ET.SubElement(
            suite, "testcase", classname="s223.fixture", name=name, file="acceptance.py"
        )
        try:
            action()
        except Exception:
            failures += 1
            # Do not expose exception bodies, environment or credentials.
            ET.SubElement(case, "failure", message="acceptance assertion failed")

    def require(condition):
        if not condition:
            raise AssertionError()

    def no_host_authority():
        for key in (
            "DOCKER_CONFIG",
            "TENDER_REGISTRY_PULL_TOKEN",
            "TENDER_REGISTRY_PREFIX",
            "TENDER_REGISTRY_TOKEN",
        ):
            require(key not in os.environ)
        require(not Path("/var/run/docker.sock").exists())

    check("checkout", lambda: require(Path("acceptance.py").is_file()))
    check("host-authority-absent", no_host_authority)
    if not args.bootstrap:
        services = json.loads(os.environ.get("TENDER_SERVICES", "[]"))
        check("service-count", lambda: require(len(services) == 2))

        def reachable(index, expected=None):
            require(len(services) == 2)
            service = services[index]
            require(service["host"] == f"svc{index}" and len(service["ports"]) == 1)
            path = "/fixture.txt" if index == 0 else "/"
            url = f"http://{service['host']}:{int(service['ports'][0])}{path}"
            last = time.monotonic() + 30
            while True:
                try:
                    with urllib.request.urlopen(url, timeout=2) as response:
                        body = response.read(4096)
                    require(body == expected if expected is not None else bool(body))
                    return
                except (OSError, urllib.error.URLError):
                    if time.monotonic() >= last:
                        raise
                    time.sleep(0.25)

        check("private-service", lambda: reachable(0, b"s223-private-service\n"))
        check("public-service", lambda: reachable(1))
    suite.set("tests", str(len(suite)))
    suite.set("failures", str(failures))
    ET.ElementTree(suite).write("result.xml", encoding="utf-8", xml_declaration=True)
    print(f"S223 fixture: {len(suite)} assertions, {failures} failures")
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
