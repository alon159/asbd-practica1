# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"

  machines = [
    { name: "master",  ip: "192.168.56.10", memory: 2048, cpus: 2 },
    { name: "worker1", ip: "192.168.56.11", memory: 1536, cpus: 1 },
    { name: "worker2", ip: "192.168.56.12", memory: 1536, cpus: 1 }
  ]

  machines.each do |machine|
    config.vm.define machine[:name] do |node|
      node.vm.hostname = machine[:name]
      node.vm.network "private_network", ip: machine[:ip]

      node.vm.provider "virtualbox" do |vb|
        vb.name = "bigdata-#{machine[:name]}"
        vb.memory = machine[:memory]
        vb.cpus = machine[:cpus]
      end

      node.vm.provision "ansible" do |ansible|
        ansible.playbook = "ansible/playbooks/deploy-bigdata.yml"
        ansible.inventory_path = "ansible/inventory/hosts.ini"
      end
    end
  end
end

