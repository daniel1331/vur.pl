#!/bin/sh

### There are two modes this source code is working in (as a result two corresponding scripts are produced):
### 1. one-click-installer - always installs the latest available version of Plesk for an environment, where the installer was executed
### 2. plesk-installer - just transparently for a user downloads autoinstaller binary, which corresponds to an environment, where the installer was executed
### 'current_mode' is defined on building stage to produce two scripts from one source
current_mode="one-click-installer"
### If non-empty, this will specify default installation source. It will end up in .autoinstallerrc as well.
override_source=""

set -efu

die()
{
	echo "ERROR: $*" >&2
	exit 1
}

verbose()
{
	if [ -n "$verbose" ]; then
		echo "$@" >&2
	fi
}

check_root()
{
	if [ `id -u` -ne 0 ]; then
		die "You should have superuser privileges to install Plesk"
	fi
}

check_for_upgrade()
{
	local prefix
	local version=
	for prefix in /opt/psa /usr/local/psa; do
		if [ -e "$prefix/version" ]; then
			version=`cat $prefix/version |  awk '{ print $1 }'`
			break
		elif [ -f "$prefix/core.version" ]; then
			version=`cat $prefix/core.version |  awk '{ print $1 }'`
			break
		fi
	done

	if [ -n "$version" ]; then
		verbose "You have Plesk v $version installed."
		if [ "$current_mode" = "one-click-installer" ]; then
			local installer_url="http://autoinstall.plesk.com/plesk-installer"
			[ -z "$override_source" ] || installer_url="$override_source/plesk-installer-cn"
			### we should stop installation of the latest available version if some Plesk version is already installed
			echo "You can't use one-click-installer since you already have Plesk installed." >&2
			echo "You should use interactive installer mode instead, to use it run 'plesk installer' in shell console." >&2
			echo "Note: to run Plesk installer using Web UI (https://<you_host>:8447) you should use --web-interface option, in other cases it will work via shell console." >&2
			exit 0
		fi
	fi
}

fetch_file()
{
	local url=$1
	local target=$2

	if [ -x "/usr/bin/wget" ]; then
		cmd="/usr/bin/wget $url -O $target"
	elif [ -x "/usr/bin/curl" ]; then
		cmd="/usr/bin/curl -fv $url -o $target"
	elif [ -x "/usr/bin/fetch" ]; then
		cmd="/usr/bin/fetch -o $target $url"
	else
		die "Unable to find download manager(fetch, wget, curl)"
	fi

	verbose "Transport command is $cmd"

	$cmd
}

fetch_url()
{
	local ai_name="$1"
	local ai_dest="$2"
	local ai_url

	shift 2
	for ai_src in "$@"; do
		ai_url="$ai_src/Parallels_Installer/$ai_name"
		fetch_file "$ai_url" "$ai_dest" && return 0
	done
	return 1
}

fetch_autoinstaller()
{
	local ai_name="$1"
	local ai_dest="$2"
	local sources
	local fetch_output=
	local fetch_rc=0

	rm -f "$ai_dest" >/dev/null 2>&1

	if [ -n "${SKIP_DEFAULT_INSTALLER_DOWNLOAD_SOURCE:+X}" ]; then
		[ -n "$source" ] || die "No source specified to download the Plesk Installer from"
		sources="$source"
	else
		sources="$source http://autoinstall.plesk.com"
	fi

	fetch_output=`fetch_url "$ai_name" "$ai_dest" $sources 2>&1` || fetch_rc=$?
	[ "$fetch_rc" -eq 0 -a -z "$verbose" ] || echo "$fetch_output"
	[ "$fetch_rc" -eq 0 ] || die "Unable to run Plesk Installer. Possible reasons:
1) You are trying to run Plesk Installer on an unsupported OS. Your OS is $os_name-$os_version. The list of supported OS is at http://docs.plesk.com/release-notes/current/software-requirements/
2) Temporary network problem. Check your connection to ${override_source:-autoinstall.plesk.com}, contact your provider or open a support ticket."

	chmod 0700 "$ai_dest"
}

put_source_into_autoinstallerrc()
{
	local source="$1"
	local ai_rc="/root/.autoinstallerrc"

	[ -n "$source" ] || return 0
	! grep -q '^\s*SOURCE\s*=' "$ai_rc" 2>/dev/null || return 0

	echo "# SOURCE value is locked by $current_mode script" >> "$ai_rc"
	echo "SOURCE = $source" >> "$ai_rc"
	chmod go-wx "$ai_rc"
}

get_os_info()
{
	[ -e '/bin/uname' ] && uname='/bin/uname' || uname='/usr/bin/uname'
	arch=`uname -m`
	local os_sn

	case $arch in
		i?86) arch="i386" ;;
		*) : ;;
	esac

	opsys=`uname -s`
	if [ "$opsys" = 'Linux' ]; then
		if [ -e '/etc/debian_version' ]; then
			if [ -e '/etc/lsb-release' ]; then
				# Mostly ubuntu, but debian can have it
				. /etc/lsb-release
				os_name=$DISTRIB_ID
				os_version=$DISTRIB_RELEASE
			else
				os_name='Debian'
				os_version=`head -1 /etc/debian_version`
			fi
			case $os_name in
				Debian) 
					os_version=`echo $os_version | grep -o "^[0-9]\+"`
					[ -z "$os_version" ] || os_version="$os_version.0"
					;;
				Ubuntu) 
					;;
				*) 
					die "Unknown OS: $os_name-$os_version-$arch"
					;;
			esac
		elif [ -e '/etc/SuSE-release' ]; then
			os_name='SuSE'
			os_version=`head -1 /etc/SuSE-release | sed -e 's/[^0-9.]*\([0-9.]*\).*/\1/g'`
			if grep -q 'Enterprise Server' /etc/SuSE-release; then
				os_version="es$os_version"
			fi
		elif [ -e '/etc/fedora-release' ]; then
			os_name='FedoraCore'
			os_version=`head -1 /etc/fedora-release | sed -e 's/[^0-9.]*\([0-9.]*\).*/\1/g'`
		elif [ -e '/etc/redhat-release' ]; then
			os_name=`awk '{print $1}' /etc/redhat-release`
			os_version=`head -1 /etc/redhat-release | sed -e 's/[^0-9.]*\([0-9.]*\).*/\1/g'`
			# for rh based os get only major
			os_version=`echo $os_version | awk -F'.' '{print $1}'`
			case $os_name$os_version$arch in
				CentOS4*i386) os_version="4.2" ;;
				CentOS4*x86_64) os_version="4.3" ;;
				CentOS*|Cloud*|Virtuozzo*) os_version=`echo $os_version | awk -F'.' '{print $1}'` ;;
				Red*) os_name="RedHat"; os_version="el`echo $os_version | awk -F'.' '{print $1}'`" ;;
				*) die "Unknown OS: $os_name-$os_version-$arch" ;;
			esac
		else
			die "Unable to detect OS"
		fi
	else
		die "Unable to detect OS"
	fi

	[ -n "$os_name" ]    || die "Unable to detect OS"
	[ -n "$os_version" ] || die "Unable to detect $os_name OS version"
	[ -n "$arch" ]       || die "Unable to detect system architecture"

	if [ "$os_name" = "RedHat" -a "$os_version" = "el7" ]; then
		os_name="CentOS"
		os_version="7"
	fi

	if [ "$os_name" = "Virtuozzo" -a "$os_version" = "7" ]; then
		os_name="VZLinux"
		os_version="7"
	fi

	verbose "Detected os $os_name-$os_version-$arch"
}

unset GREP_OPTIONS

verbose=
dry_run=
os_name=
os_version=
arch=
source="$override_source"
tiers="release,stable"

parse_args()
{
	while [ "$#" -gt 0 ]; do
		case "$1" in
			--source)
				source="$2"
				[ "$#" -ge 2 ] && shift 2 || break
				;;
			--tier)
				[ "$current_mode" != "one-click-installer" ] || tiers="$2"
				[ "$#" -ge 2 ] && shift 2 || break
				;;
			-v)
				[ "$current_mode" != "one-click-installer" ] || verbose=1
				shift
				;;
			-n)
				[ "$current_mode" != "one-click-installer" ] || dry_run=1
				shift
				;;
			*)
				shift
				;;
		esac
	done
}

parse_args "$@"
check_root
check_for_upgrade

get_os_info

ai_name="parallels_installer_${os_name}_${os_version}_${arch}"
ai_dest='/var/cache/parallels_installer/installer'
ai_dest_dir=`dirname $ai_dest`
if [ ! -d  "$ai_dest_dir" ]; then
	mkdir -p "$ai_dest_dir"
	chmod 0700 "$ai_dest_dir"
fi
fetch_autoinstaller "$ai_name" "$ai_dest"

[ -n "$dry_run" ] || put_source_into_autoinstallerrc "$source"

ai_args=
if [ "$current_mode" = "one-click-installer" ]; then
	ai_args="--select-product-id plesk --select-release-latest --tier $tiers --installation-type Typical"
	[ -z "$source" ] || ai_args="$ai_args --source $source"
fi

if [ -n "$ai_args" ]; then
	verbose "The following command will run: $ai_dest $ai_args"
	[ -n "$dry_run" ] || exec "$ai_dest" $ai_args
else
	if [ -n "$override_source" -a "$override_source" = "$source" ]; then
		# if --source wasn't overriden on command line, but is overriden in the script, then enforce its value
		ai_args="$ai_args --source $source"
	fi

	verbose "The following command will run: $ai_dest $* $ai_args"
	[ -n "$dry_run" ] || exec "$ai_dest" "$@" $ai_args
fi

[ -z "$dry_run" ] || rm -f "$ai_dest"