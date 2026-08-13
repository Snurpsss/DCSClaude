-- =====================================================================
--  Claude Copilot - Canal de COMMANDE vers la mission (sans DCS-gRPC)
--
--  À placer dans : Saved Games\DCS\Scripts\Hooks\dcs_claude_control.lua
--
--  Ouvre un socket UDP loopback (127.0.0.1:5011). Chaque datagramme reçu
--  est du code Lua exécuté DANS l'environnement de mission via
--  net.dostring_in('mission', ...). La valeur renvoyée (ou "OK"/"ERR") est
--  retournée à l'expéditeur.
--
--  Le pompage se fait dans onSimulationFrame -> il faut être EN MISSION
--  (mission chargée et non en pause) pour que les commandes s'exécutent.
--
--  Aucune modification de MissionScripting.lua (env. des hooks non restreint).
--  N'écoute QUE sur 127.0.0.1.
-- =====================================================================

local ok, socket = pcall(require, "socket")
if not ok then
    log.write("CLAUDE_CTRL", log.ERROR, "LuaSocket indisponible : " .. tostring(socket))
    return
end

local HOST, PORT = "127.0.0.1", 5011
local udp = socket.udp()
udp:settimeout(0)
local bound, err = udp:setsockname(HOST, PORT)
if not bound then
    log.write("CLAUDE_CTRL", log.ERROR, "bind échoué : " .. tostring(err))
    return
end

-- Diagnostic : la fonction d'injection est-elle disponible dans cet environnement ?
local have_net = (type(net) == "table" and type(net.dostring_in) == "function")
log.write("CLAUDE_CTRL", log.INFO,
    "Canal prêt sur " .. HOST .. ":" .. PORT ..
    " | net.dostring_in dispo = " .. tostring(have_net))

local function run_in_mission(code)
    if not have_net then
        return "ERR: net.dostring_in indisponible dans cet environnement"
    end
    local ok2, res = pcall(net.dostring_in, "mission", code)
    if ok2 then
        return (res ~= nil) and tostring(res) or "OK"
    end
    return "ERR: " .. tostring(res)
end

local function pump()
    while true do
        local data, ip, port = udp:receivefrom()
        if not data then break end
        local reply = run_in_mission(data)
        log.write("CLAUDE_CTRL", log.INFO,
            "recv(" .. #data .. "o) -> " .. tostring(reply))
        if ip and port then
            udp:sendto(reply, ip, port)
        end
    end
end

local callbacks = {}
function callbacks.onSimulationFrame() pump() end
-- Pompe aussi hors mission (menu) pour que le bouton « Tester » réponde même
-- si aucune mission n'est chargée (les commandes mission échoueront alors
-- proprement, mais le canal prouve qu'il vit).
function callbacks.onShowRadioMenu() pump() end
DCS.setUserCallbacks(callbacks)
