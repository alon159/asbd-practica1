# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"
  config.vm.boot_timeout = 600

  # Nodos del clúster con recursos optimizados
  nodes = [
    { name: "master",  ip: "192.168.56.10", cpus: 1, memory: 1536, ports: [[9870, 9870], [8080, 8080], [4040, 4040]] },
    { name: "worker1", ip: "192.168.56.11", cpus: 1, memory: 1280, ports: [[8081, 8081], [9864, 9864]] },
    { name: "worker2", ip: "192.168.56.12", cpus: 1, memory: 1280, ports: [[8081, 8082], [9864, 9865]] }
  ]

  nodes.each do |node_info|
    config.vm.define node_info[:name] do |node|
      node.vm.hostname = node_info[:name]
      node.vm.network "private_network", ip: node_info[:ip]

      # Reenvío de puertos para acceder a las interfaces web desde el host
      node_info[:ports].each do |guest_port, host_port|
        node.vm.network "forwarded_port", guest: guest_port, host: host_port, auto_correct: true
      end

      # Configuración de recursos en VirtualBox
      node.vm.provider "virtualbox" do |vb|
        vb.name = "asbd-#{node_info[:name]}"
        vb.memory = node_info[:memory]
        vb.cpus = node_info[:cpus]
        vb.customize ["modifyvm", :id, "--audio", "none"]
        vb.customize ["modifyvm", :id, "--paravirtprovider", "hyperv"]
      end

      # Aprovisionamiento con Ansible Local
      node.vm.provision "ansible_local" do |ansible|
        ansible.playbook = "ansible/site.yml"
        ansible.inventory_path = "ansible/inventory.ini"
        ansible.limit = node_info[:name]
        ansible.install = true
      end
    end
  end
end
