param([Parameter(Mandatory=$true)][string]$WordsFile, [Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$fixtureWords = Get-Content -LiteralPath $WordsFile -Raw -Encoding UTF8 | ConvertFrom-Json
[System.IO.Directory]::CreateDirectory($OutputDirectory) | Out-Null
$fixtureSpeaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $fixtureSpeaker.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Male, [System.Speech.Synthesis.VoiceAge]::Adult, 0, [System.Globalization.CultureInfo]::GetCultureInfo('en-US'))
    $fixtureSpeaker.Rate = -1
    $fixtureFormat = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(22050, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
    for ($fixtureIndex = 0; $fixtureIndex -lt $fixtureWords.Count; $fixtureIndex++) {
        $fixtureFile = Join-Path $OutputDirectory ('{0:d3}.wav' -f $fixtureIndex)
        $fixtureSpeaker.SetOutputToWaveFile($fixtureFile, $fixtureFormat)
        $fixtureSpeaker.Speak([string]$fixtureWords[$fixtureIndex])
        $fixtureSpeaker.SetOutputToNull()
    }
} finally {
    $fixtureSpeaker.Dispose()
}
