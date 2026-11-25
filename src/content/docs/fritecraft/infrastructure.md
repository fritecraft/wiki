---
title: "Infrastructure"
---

Cette page est dédiée aux personnes qui s’y connaissent en informatique et qui voudraient en apprendre plus sur le projet Fritecraft.
## Version 2017-2021
Le serveur de jeu est exécuté sur un serveur physique entreprise (PowerEdge R710) type datacenter, et dispose ainsi de généreuses ressources :
- CPU : Intel(R) Xeon(R) CPU X5672 @ 3.20GHz (2 socket, 4 coeurs, hyperthreading)
- Mémoire : 144 Go DDR3 1330 MHz
- 4 NIC 1Gbit/s
- 2 alim 750W
- 6 Disques SATA en RAID5
La VM qui fait tout tourner dispose de 64 Go de RAM et de 16 cœurs logiques.
Afin d’optimiser l’exécution au mieux, il a été choisi de scinder les mondes en différentes “instances”, grâce à la technologie de proxy Bungeecord (fork Waterfall, plus optimisé). Plus précisément, chaque monde est un conteneur Docker. Et donc, chaque conteneur dispose de ses propres plugins. Cependant, comme certains plugins sont communs à tout les mondes, et partagent des fichiers, des volumes communs ont été monté sur les conteneurs pour le partage de configurations et données. De nombreux plugins enregistrent leurs données en base MySQL, le partage des données est donc facile.
Le serveur dispose de 6 disque dur en RAID 5, mais pour optimiser les performances, un RAMdisk (tmpfs) a été configuré afin de charger les fichiers des mondes directement en RAM, offrant des IOPS dépassant n'importe quel SSD. Le risque associé est qu'en cas de coupure de courant ou crash, les données non copiées sur disque seraient perdu, un script synchronise donc les données à intervalles réguliers. Le serveur est directement branché sur un onduleur 600W, chargé à 40% de capacité, offrant donc environ 15 minutes d'autonomie en cas de coupure électrique.
Tout a été pensé pour la sécurité : les sauvegardes sont assurées directement à la couche VMWare grâce à Veeam. Les dumps bases de données sont effectués à intervalles réguliers. La supervision est assurée à la fois par PRTG pour la VM, et au niveau de Netdata pour les conteneurs, et l'exécution automatique des scripts par la crontab est surveillée par un service externe (healthchecks.io).
Le site Web (stack docker compose Wordpress) ainsi que le Wiki (Bookstack) sont exécutés également avec Docker. Les connexions HTTPS sont servies en reverse proxy grâce à Caddy v2, avec un renouvellement automatique des certificats.
Un deuxième serveur de type NAS héberge les services tels que le wiki et le site, ainsi que les sauvegardes.
## Version 2022
Le serveur est toujours hébergé sur le même matériel. Seuls les disques ont changés : les disques SATA standards ont été remplacés par des disques SAS 15K RPM. De plus, le serveur n'est plus exécuté dans une machine virtuelle Debian.
Le serveur a été réinstallé sous Red Hat Enterprise Linux 8.6, directement sur le matériel (bare-metal) pour supprimer la couche d'abstraction matérielle et donc gagner en performances.
Le wiki a été migré sur la plateforme WikiJS, proposant une navigation plus claire.
Tous les services sont proposés au travers de l'infrastructure Cloudflare, qui offre des protections réseau, mais aussi des systèmes d'authentification avancée.
## Ramdisk
Pour des meilleures performances, le serveur utilise un script personnalisé pour générer un ramdisk, c'est à dire un disque virtuel en RAM, bien plus rapide que les SSD du marché. Le serveur dispose de 144Go de RAM (18 barretes de 8Go), un ramdisk de 44Go permet de stocker toutes les cartes du jeu et data, tout en laissant suffisamment de RAM pour les programmes.
Au lancement du serveur, les données sur disques sont copiées dans le ramdisk, qui est ensuite périodiquement synchronisé sur les disques. En cas de coupure du serveur, les données non synchronisées seront perdues, car la RAM est volatile, c'est le principal inconvénient du ramdisk.
### Performances E/S par secondes : lectures/écritures aléatoires
fio --filename=test --size=20GB --direct=1 --rw=randrw --bs=4k --ioengine=libaio --iodepth=256 --runtime=120 --numjobs=4 --time_based --group_reporting --name=iops-test-job --eta-newline=1
Disques
  read: IOPS=302, BW=1211KiB/s (1240kB/s)(142MiB/120010msec)
  write: IOPS=305, BW=1221KiB/s (1250kB/s)(143MiB/120010msec)
ramdisk
  read: IOPS=455k, BW=1779MiB/s (1865MB/s)(208GiB/120001msec)
  write: IOPS=455k, BW=1779MiB/s (1865MB/s)(208GiB/120001msec)
On a presque une différence de x1000
### Performances de débit : lectures/ecritures aléatoires
fio --filename=test --size=20GB -rw=randrw --bs=64k --ioengine=libaio --iodepth=64 --runtime=120 --numjobs=4 --time_based --group_reporting --name=throughput-test-job --eta-newline=1 
Disques
Ramdisk
### Performancces de latences : léctures/écritures aléatoires
fio --filename=test --size=20GB --rw=randrw --bs=4k --ioengine=libaio --iodepth=1 --numjobs=1 --time_based --group_reporting --name=rwlatency-test-job --runtime=120 --eta-newline=1
Disques
  read: IOPS=224, BW=898KiB/s (920kB/s)(105MiB/120003msec)
    lat (usec): min=283, max=252526, avg=4428.53, stdev=7063.33
  write: IOPS=224, BW=898KiB/s (919kB/s)(105MiB/120003msec)
    lat (usec): min=4, max=132, avg=17.03, stdev= 7.34
Ramdisk
  read: IOPS=150k, BW=587MiB/s (616MB/s)(68.8GiB/120001msec)
    lat (nsec): min=2005, max=154512, avg=2586.71, stdev=559.00
  write: IOPS=150k, BW=587MiB/s (616MB/s)(68.8GiB/120001msec)
    lat (nsec): min=2179, max=144927, avg=2823.40, stdev=563.80
Au niveau de la latence en lecture, on est environ à 2,5 microsecondes pour le ramdisk, contre 4428 pour les disques.
