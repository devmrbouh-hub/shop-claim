NSSM (Non-Sucking Service Manager) — optional for install.ps1 service setup.



Preferred build (Win10 / Server 2016+): nssm 2.24-101 win64

Direct zip: https://nssm.cc/ci/nssm-2.24-101-g897c7ad.zip

SHA256 zip: 99F5045FFFBFFB745D67FE3A065A953C4A3D9C253B868892D9B685B0EE7D07B8



Extract win64\nssm.exe -> release\tools\nssm.exe



nssm.cc often returns 503 — retry a few times or download from another network.

Stable release link (nssm-2.24.zip) is often down; do not use on Server 2016+.



Alternatives if download keeps failing:

- install.ps1 -SkipService (run shop-claim-bridge.exe manually or via Task Scheduler)

- winget install NSSM.NSSM  (on VDS with winget)

- copy nssm.exe from another machine



build-release.ps1 bundles tools\nssm.exe if present; otherwise tries CI zip with retries.


