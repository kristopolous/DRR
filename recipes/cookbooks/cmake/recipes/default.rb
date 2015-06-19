#
# Cookbook Name:: cmake
# Recipe:: default
#

case node[:platform]
when "centos","fedora","redhat"
  package "cmake28"
when "ubuntu","debian"
  package "cmake"
end
