-- Zomboid Aura 0.1 alpha. Client-only, no Java/native injection.
ZomboidAura = ZomboidAura or {}
local ZA = ZomboidAura
ZA.routes = ZA.routes or {}
ZA.sounds = {}
ZA.seq = 0
ZA.session = tostring(getTimestampMs())
ZA.lastWrite = 0
ZA.telemetryStopped = false
ZA.captureWorld = false -- Opt-in: world AI noise is not the same as audible FMOD audio.
ZA.modes = {"off", "health", "endurance", "sound", "combined"}
ZA.categories = {"all", "world", "zombie", "vehicle", "player", "gunshot", "alarm"}
local warned = {}
local function warnOnce(key, value)
    if not warned[key] then print("[ZomboidAura] " .. key .. ": " .. tostring(value)); warned[key] = true end
end
local function contains(list, value)
    for _, v in ipairs(list) do if v == value then return true end end
    return false
end
local function quote(value)
    return '"' .. tostring(value):gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\n', '\\n'):gsub('\r', '\\r'):gsub('\t', '\\t') .. '"'
end
local function number(value, lo, hi)
    value = tonumber(value)
    if not value or value ~= value or value == math.huge or value == -math.huge then return nil end
    return math.max(lo, math.min(hi, value))
end
local function readLines(path)
    local lines, reader = {}, nil
    local ok, err = pcall(function()
        reader = getFileReader(path, false)
        if reader then
            local line = reader:readLine()
            while line do
                if #lines >= 512 then break end
                lines[#lines + 1] = tostring(line)
                line = reader:readLine()
            end
        end
    end)
    if reader then pcall(function() reader:close() end) end
    if not ok then warnOnce("read " .. path, err) end
    return lines
end
local function writeFile(path, text)
    local writer
    local ok, err = pcall(function()
        writer = getFileWriter(path, true, false)
        if not writer then error("No file writer") end
        writer:write(text)
    end)
    if writer then
        local closed, closeErr = pcall(function() writer:close() end)
        if not closed then ok = false; err = closeErr end
    end
    if not ok then warnOnce("write " .. path, err) end
    return ok
end
function ZA.loadConfig()
    for _, line in ipairs(readLines("za-settings.tsv")) do
        if line == "world\t1" then ZA.captureWorld = true end
        local id, mode, player, bright, category = line:match("^([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)$")
        if id and contains(ZA.modes, mode) and contains(ZA.categories, category) then
            local p, b = number(player, 0, 3), number(bright, 0, 1)
            if p and b then ZA.routes[id] = {target=id, mode=mode, player=math.floor(p), brightness=b, category=category} end
        end
    end
end
function ZA.saveConfig()
    local lines = {"world\t" .. (ZA.captureWorld and "1" or "0")}
    for id, route in pairs(ZA.routes) do
        lines[#lines+1] = table.concat({id, route.mode, tostring(route.player), tostring(route.brightness), route.category}, "\t")
    end
    return writeFile("za-settings.tsv", table.concat(lines, "\n") .. "\n")
end
function ZA.devices()
    local lines = readLines("za-devices.tsv")
    local devices = {}
    if lines[1] ~= "ZA1" then return devices end
    for i=2, #lines do
        local id, name = lines[i]:match("^([^\t]+)\t(.+)$")
        if id and #id <= 100 then
            devices[#devices+1] = {id=id, name=name}
            ZA.routes[id] = ZA.routes[id] or {target=id, mode="off", player=0, brightness=0.35, category="all"}
        end
    end
    return devices
end
-- Adapter API: call ONLY for an event already accepted as audible for this player.
-- category: world/zombie/vehicle/player/gunshot/alarm, playerIndex is optional.
-- This is an extension point, not an automatic Visual Sounds adapter.
function ZA.pushSound(x, y, z, strength, category, playerIndex, source)
    x, y, z = tonumber(x), tonumber(y), tonumber(z)
    strength = number(strength, 0, 1)
    if not x or not y or not z or not strength or not contains(ZA.categories, category) or category == "all" then return end
    if x ~= x or y ~= y or z ~= z then return end
    local now = getTimestampMs()
    -- Coalesce repeating emitters; cap work and storage during busy scenes.
    for i=#ZA.sounds,1,-1 do
        local s = ZA.sounds[i]
        if now-s.time > 1200 then table.remove(ZA.sounds,i)
        elseif s.x == x and s.y == y and s.z == z and s.category == category and s.player == playerIndex then
            s.time=now; s.strength=strength; s.source=source; return
        end
    end
    if #ZA.sounds >= 32 then table.remove(ZA.sounds,1) end
    ZA.sounds[#ZA.sounds+1] = {x=x,y=y,z=z,strength=strength,category=category,player=playerIndex,source=source,time=now}
end
local function onWorldSound(x,y,z,radius,volume,source)
    if not ZA.captureWorld then return end
    radius = tonumber(radius) or 0
    if radius <= 0 then return end
    local category = "world"
    if source and instanceof then
        if instanceof(source, "IsoZombie") then category="zombie"
        elseif instanceof(source, "BaseVehicle") then category="vehicle"
        elseif instanceof(source, "IsoPlayer") then category="player" end
    end
    -- World event strength uses radius, not FMOD loudness. No sound-name guessing.
    for i=0,3 do
        local player = getSpecificPlayer(i)
        if player and player ~= source then
            local dx, dy = x-player:getX(), y-player:getY()
            local distance = math.sqrt(dx*dx+dy*dy) + math.abs(z-player:getZ())*8
            if distance <= radius then
                ZA.pushSound(x,y,z,math.max(0, 1-distance/radius),category,i,source)
            end
        end
    end
end
-- B42 uses CharacterStat; B41 exposes the legacy getter.
local function enduranceValue(player)
    local stats = player:getStats()
    if CharacterStat and CharacterStat.ENDURANCE and stats.get then
        return number(stats:get(CharacterStat.ENDURANCE), 0, 1)
    elseif stats.getEndurance then
        return number(stats:getEndurance(), 0, 1)
    end
    error("Unsupported endurance API; telemetry stopped until reload")
end
local function playerJSON(player, index, now)
    local health = number(player:getBodyDamage():getOverallBodyHealth()/100, 0, 1) or 0
    local endurance = enduranceValue(player)
    if endurance == nil then error("Invalid endurance; telemetry stopped until reload") end
    local sounds = {}
    for _, s in ipairs(ZA.sounds) do
        local age = (now-s.time)/1000
        if age >= 0 and age < 1.2 and (s.player == nil or s.player == index) and s.source ~= player then
            local dx,dy = s.x-player:getX(), s.y-player:getY()
            -- Zomboid's isometric projection: screen X=(x-y), screen Y=(x+y)/2.
            local sx,sy = dx-dy, (dx+dy)*0.5
            local bearing = math.atan2(sx, -sy)
            sounds[#sounds+1] = '{"bearing":'..tostring(bearing)..',"strength":'..tostring(s.strength)..',"age":'..tostring(age)..',"category":'..quote(s.category)..'}'
        end
    end
    return '{"id":'..index..',"health":'..health..',"endurance":'..endurance..',"sounds":['..table.concat(sounds,',')..']}'
end
function ZA.tick()
    if ZA.telemetryStopped then return end
    local now = getTimestampMs()
    if now-ZA.lastWrite < 100 then return end
    ZA.lastWrite = now
    local ok, err = pcall(function()
        local players, routes = {}, {}
        for i=0,3 do
            local player = getSpecificPlayer(i)
            if player then players[#players+1] = playerJSON(player,i,now) end
        end
        for _, route in pairs(ZA.routes) do
            routes[#routes+1] = '{"target":'..quote(route.target)..',"mode":'..quote(route.mode)..',"player":'..route.player..',"brightness":'..route.brightness..',"category":'..quote(route.category)..'}'
        end
        ZA.seq = ZA.seq+1
        local frame = '{"protocol":1,"session":'..quote(ZA.session)..',"seq":'..ZA.seq..',"players":['..table.concat(players,',')..'],"routes":['..table.concat(routes,',')..']}'
        writeFile("za-frame-"..tostring(ZA.seq % 2)..".json",frame.."\n")
    end)
    if not ok then
        ZA.telemetryStopped = true -- Kahlua logs even errors caught by pcall. Never retry each tick.
        warnOnce("telemetry stopped until reload",err)
    end
end
ZA.loadConfig()
Events.OnTick.Add(ZA.tick)
if Events.OnWorldSound then Events.OnWorldSound.Add(onWorldSound) end
