%define sign_server 10.12.65.118

%global with_debuginfo 0
%if 0%{?rhel} == 6
%global dist .tl1
%global debug_path /usr/lib/debug/lib/
%else
%global debug_path /usr/lib/debug/usr/lib/
%if 0%{?rhel} == 7
%global dist .tl2
%endif
%endif

%if 0%{?rhel} == 8
%global __python %{__python2}
%endif

%global build_env DESTDIR="%{buildroot}" prefix=%{_prefix} lib=%{_lib} PYTHON=%{__python3} INSTALL_ROOT=%{buildroot}
%global bpftool_make make %{?_smp_mflags} -C tools/bpf/bpftool %{build_env} mandir=%{_mandir} bash_compdir=%{_sysconfdir}/bash_completion.d/

# Architectures we build tools/cpupower on
%define cpupowerarchs x86_64 aarch64

Summary: Performance monitoring for the Linux kernel
Group: Development/System
Name: %{name}
Version: %{version}
Release: %{release_os}%{?dist}
License: GPLv2
Vendor: Tencent
Packager: tlinux team <g_CAPD_SRDC_OS@tencent.com>
Provides: perf = %{version}-%{release}
Source0: %{name}-%{version}.tar.gz
# Sources for kernel tools
Source2000: cpupower.service
Source2001: cpupower.config
URL: http://www.tencent.com
ExclusiveArch:  x86_64
Distribution: Tencent Linux
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-build
BuildRequires: wget bc module-init-tools curl
BuildRequires: elfutils-devel zlib-devel binutils-devel newt-devel perl(ExtUtils::Embed) bison flex
%if 0%{?rhel} == 8
BuildRequires: python2-devel
%else
BuildRequires: python-devel
%endif
BuildRequires: xmlto asciidoc
BuildRequires: audit-libs-devel
%ifnarch s390 s390x
BuildRequires: numactl-devel
%endif
# kernel tools
BuildRequires: gettext ncurses-devel asciidoc
%ifnarch s390x
BuildRequires: pciutils-devel
BuildRequires: libcap-devel
%endif

# for the 'hostname' command
%if 0%{?rhel} == 7
BuildRequires: hostname
%else
BuildRequires: net-tools
%endif

%description
This package contains the perf tool, which enables performance monitoring
of the Linux kernel.


%package -n python-perf
Summary: Python bindings for apps which will manipulate perf events
Group: Development/Libraries
%description -n python-perf
The python-perf package contains a module that permits applications
written in the Python programming language to use the interface
to manipulate perf events.

%package -n kernel-tools
Summary: Assortment of tools for the Linux kernel
Group: Development/System
License: GPLv2
%ifarch %{cpupowerarchs}
Provides:  cpupowerutils = 1:009-0.6.p1
Obsoletes: cpupowerutils < 1:009-0.6.p1
Provides:  cpufreq-utils = 1:009-0.6.p1
Provides:  cpufrequtils = 1:009-0.6.p1
Obsoletes: cpufreq-utils < 1:009-0.6.p1
Obsoletes: cpufrequtils < 1:009-0.6.p1
Obsoletes: cpuspeed < 1:1.5-16
%endif
%description -n kernel-tools
This package contains the tools/ directory from the kernel source
and the supporting documentation.

%package -n kernel-tools-libs
Summary: Libraries for the kernel-tools
Group: Development/System
License: GPLv2
%description -n kernel-tools-libs
This package contains the libraries built from the tools/ directory
from the kernel source.

%package -n bpftool
Summary: Inspection and simple manipulation of eBPF programs and maps
License: GPLv2
BuildRequires: llvm
%if 0%{?rhel} == 7
BuildRequires: python2-docutils
%else
BuildRequires: python3-docutils
%endif
%description -n bpftool
This package contains the bpftool, which allows inspection and simple
manipulation of eBPF programs and maps.

%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib(1)")}


# prep #########################################################################
%prep

%setup -q -c -T -a 0

# build ########################################################################
%build


if [ ! -f /etc/tlinux-release ]; then
	echo "Error: please build this rpm on tlinux\n"
	exit 1
fi


cd %{name}-%{version}
all_types="%{kernel_all_types}"
num_processor=`cat /proc/cpuinfo | grep 'processor' | wc -l`
if [ $num_processor -gt 8 ]; then
    num_processor=8
fi

%global perf_make make %{?_smp_mflags} -C tools/perf -s V=1 WERROR=0 NO_LIBUNWIND=1 HAVE_CPLUS_DEMANGLE=1 NO_GTK2=1 NO_STRLCPY=1 prefix=%{_prefix} lib=%{_lib}
# perf
%{perf_make} all
%{perf_make} man

# kernel tools
%ifarch %{cpupowerarchs}
# cpupower
# make sure version-gen.sh is executable.
chmod +x tools/power/cpupower/utils/version-gen.sh
make %{?_smp_mflags} -C tools/power/cpupower bash_completion_dir=%{_sysconfdir}/bash_completion.d/ CPUFREQ_BENCH=false
%ifarch x86_64
	pushd tools/power/cpupower/debug/x86_64
	make %{?_smp_mflags} centrino-decode powernow-k8-decode
	popd
%endif
%ifarch x86_64
	pushd tools/power/x86/x86_energy_perf_policy/
	make
	popd
	pushd tools/power/x86/turbostat
	make
	popd
%endif #turbostat/x86_energy_perf_policy
%endif
pushd tools
make tmon
popd

%{bpftool_make}

# install ######################################################################
%install
cd %{name}-%{version}
%{perf_make} DESTDIR=$RPM_BUILD_ROOT install
mkdir -p %{buildroot}%{_libdir}
touch %{buildroot}%{_libdir}/libperf-jvmti.so
rm -f %{buildroot}%{_bindir}/trace

# perf-python extension
%{perf_make} DESTDIR=$RPM_BUILD_ROOT install-python_ext

# perf man pages (note: implicit rpm magic compresses them later)
%{perf_make} DESTDIR=$RPM_BUILD_ROOT install-man

# kernel tools
%ifarch %{cpupowerarchs}
make -C tools/power/cpupower DESTDIR=$RPM_BUILD_ROOT libdir=%{_libdir} mandir=%{_mandir} bash_completion_dir=%{_sysconfdir}/bash_completion.d/ CPUFREQ_BENCH=false install
rm -f %{buildroot}%{_libdir}/*.{a,la}
%find_lang cpupower
mv cpupower.lang ../
%ifarch x86_64
	pushd tools/power/cpupower/debug/x86_64
	install -m755 centrino-decode %{buildroot}%{_bindir}/centrino-decode
	install -m755 powernow-k8-decode %{buildroot}%{_bindir}/powernow-k8-decode
	popd
%endif
chmod 0755 %{buildroot}%{_libdir}/libcpupower.so*
mkdir -p %{buildroot}%{_unitdir} %{buildroot}%{_sysconfdir}/sysconfig
install -m644 %{SOURCE2000} %{buildroot}%{_unitdir}/cpupower.service
install -m644 %{SOURCE2001} %{buildroot}%{_sysconfdir}/sysconfig/cpupower
%ifarch %{ix86} x86_64
	mkdir -p %{buildroot}%{_mandir}/man8
	pushd tools/power/x86/x86_energy_perf_policy
	make DESTDIR=%{buildroot} install
	popd
	pushd tools/power/x86/turbostat
	make DESTDIR=%{buildroot} install
	popd
%endif #turbostat/x86_energy_perf_policy
pushd tools/thermal/tmon
make INSTALL_ROOT=%{buildroot} install
popd
%endif

%{bpftool_make} install doc-install
/usr/lib/rpm/brp-compress

%pre
# pre #########################################################################
system_arch=`uname -m`

if [ %{_target_cpu} != ${system_arch} ]; then
	echo "ERROR: Failed installing this rpm!!!!"
	echo "This rpm is intended for %{_target_cpu} platform. It seems your system is ${system_arch}.";
	exit 1;
fi;

if [ ! -f /etc/tlinux-release -o ! -f /etc/redhat-release ]; then
	echo "Error: Cannot install this rpm on non-tlinux OS"
	exit 1;
fi

%post
# post #########################################################################


%postun

%files
%defattr(-,root,root)
%{_bindir}/perf*
%{_sysconfdir}/bash_completion.d/perf
%dir %{_prefix}/lib/perf
%{_prefix}/lib/perf/*
%dir %{_libdir}/traceevent/
%{_libdir}/traceevent/*
%{_libdir}/libperf-jvmti.so
%dir %{_libexecdir}/perf-core
%{_libexecdir}/perf-core/*
%{_datadir}/perf-core/*
%{_docdir}/perf-tip/tips.txt
%{_mandir}/man[1-8]/perf*

%files -n python-perf
%defattr(-,root,root)
%{python_sitearch}

# kernel tools
%files -n kernel-tools -f cpupower.lang
%defattr(-,root,root)
%ifarch %{cpupowerarchs}
%{_bindir}/cpupower
%ifarch x86_64
%{_bindir}/centrino-decode
%{_bindir}/powernow-k8-decode
%endif
%{_unitdir}/cpupower.service
%{_mandir}/man[1-8]/cpupower*
%config(noreplace) %{_sysconfdir}/sysconfig/cpupower
%ifarch %{ix86} x86_64
%{_bindir}/x86_energy_perf_policy
%{_mandir}/man8/x86_energy_perf_policy*
%{_bindir}/turbostat
%{_mandir}/man8/turbostat*
%endif
%endif
%{_bindir}/tmon
%{_sysconfdir}/bash_completion.d/cpupower
%{_oldincludedir}/cpu*.h

%ifarch %{cpupowerarchs}
%files -n kernel-tools-libs
%defattr(-,root,root)
%{_libdir}/libcpupower.so*
%endif

%files -n bpftool
%defattr(-,root,root)
%{_sbindir}/bpftool
%{_sysconfdir}/bash_completion.d/bpftool
%{_mandir}/man8/bpftool*.gz
%{_mandir}/man7/bpf-helpers.7.gz

# changelog  ###################################################################
%changelog
* Thu Feb 2 2012 Samuel Liao <samuelliao@tencent.com>
 - Initial 3.0.18 repository
