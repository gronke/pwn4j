categories = {"external"}

local http = require "http"
local json = require "json"
local nmap = require "nmap"
local nsedebug = require "nsedebug"

post_json_object = function(path, request_body)
  http.post(
    "127.0.0.1",
    5000,
    path,
    {
      header = {
        ["Content-Type"] = "application/json",
      },
      scheme = "http"
    },
    nil,
    request_body
  )
end

action = function(host, port)
  local addr_family = #host.bin_ip == 4 and "IPv4" or "IPv6"

  post_json_object("Address", json.generate(json.make_object({
    ip = host.ip,
    properties = {
      name = host.name,
      family = addr_family,
      reverse_dns_hostname = host.name,
      target_name = host.targetname,
      mac_addr = host.mac_addr,
      mac_addr_next_hop = host.mac_addr_next_hop,
      os_name = host.os and host.os.name or nil,
      os_fingerprint = host.os_fp
    }
  })))

  if (port ~= nil) then
    post_json_object("Service", json.generate(json.make_object({
      properties = {
        port = port.number,
        protocol = port.protocol,
        state = port.state,
        service = port.service,
        software = port.version and port.version.name or nil
      },
      address = {
        ip = host.ip,
        family = addr_family
      }
    })))
  end
end

hostrule = function( host )
  return true
end

portrule = function(host, port)
  return true
end
