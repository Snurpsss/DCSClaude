-- =====================================================================
--  Claude Copilot - Export télémétrie DCS (fichier inclus)
--
--  À placer dans : Saved Games\DCS\Scripts\dcs_claude_export.lua
--  Puis ajouter UNE ligne à la fin de ton Export.lua :
--
--     dofile(lfs.writedir()..[[Scripts\dcs_claude_export.lua]])
--
--  Envoie l'état de vol du joueur en UDP JSON vers 127.0.0.1:5010,
--  ~10x/s. Utilise LuaSocket (fourni par DCS dans l'env d'export ;
--  aucune modif de MissionScripting.lua). Chaîne proprement les
--  callbacks existants (SRS, Tacview...) pour ne rien casser.
-- =====================================================================

local socket = require("socket")
local UDP_HOST, UDP_PORT = "127.0.0.1", 5010
local udp = socket.udp()
udp:settimeout(0)

-- On sauvegarde les callbacks déjà en place pour les rappeler.
local Prev_Start    = LuaExportStart
local Prev_Stop     = LuaExportStop
local Prev_Activity = LuaExportActivityNextEvent

local function deg(rad) return (rad or 0) * 180.0 / math.pi end

LuaExportStart = function()
    if Prev_Start then Prev_Start() end
end

LuaExportActivityNextEvent = function(t)
    pcall(function()
        local d = LoGetSelfData()
        if d and d.LatLongAlt then
            local hdg = deg(d.Heading)
            if hdg < 0 then hdg = hdg + 360 end
            local payload = string.format(
                '{"t":%.1f,"aircraft":"%s","lat":%.6f,"lon":%.6f,"alt_m":%.1f,'
                .. '"hdg":%.1f,"pitch":%.1f,"bank":%.1f,"ias_ms":%.1f,"tas_ms":%.1f,'
                .. '"mach":%.3f,"vv_ms":%.1f,"agl_m":%.1f}',
                t,
                d.Name or "unknown",
                d.LatLongAlt.Lat, d.LatLongAlt.Long, d.LatLongAlt.Alt,
                hdg, deg(d.Pitch), deg(d.Bank),
                LoGetIndicatedAirSpeed()        or 0,
                LoGetTrueAirSpeed()             or 0,
                LoGetMachNumber()               or 0,
                LoGetVerticalVelocity()         or 0,
                LoGetAltitudeAboveGroundLevel() or 0
            )
            udp:sendto(payload, UDP_HOST, UDP_PORT)
        end
    end)
    -- On n'interrompt jamais la boucle d'export, même en cas d'erreur.

    local nextT = t + 0.1
    if Prev_Activity then
        local ok, r = pcall(Prev_Activity, t)
        if ok and type(r) == "number" then nextT = math.min(nextT, r) end
    end
    return nextT
end

LuaExportStop = function()
    pcall(function() if udp then udp:close() end end)
    if Prev_Stop then Prev_Stop() end
end
