INSERT DATA {
  GRAPH <https://example.org/mv> {
<https://example.org/mv#task_translation> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#TranslationTask> .
<https://example.org/mv#task_subtitle_gen> <https://example.org/mv#status> "completed" .
<https://example.org/mv#task_subtitle_gen> <http://www.w3.org/2000/01/rdf-schema#label> "타임라인 자막 싱크 작업"@ko .
<https://example.org/mv#e2e_project_01> <https://example.org/mv#hasBrief> <https://example.org/mv#e2e_project_01_brief> .
<https://example.org/mv#task_translation> <https://example.org/mv#dependsOn> <https://example.org/mv#task_lyric_gen> .
<https://example.org/mv#task_translation> <https://example.org/mv#status> "completed" .
<https://example.org/mv#e2e_project_01> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#MusicVideoProject> .
<https://example.org/mv#audio_main> <https://example.org/mv#lyricText> "화려한 네온사인 아래 달리는 도시의 밤" .
<https://example.org/mv#audio_main> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#AudioAsset> .
<https://example.org/mv#timeline_main> <https://example.org/mv#hasShot> <https://example.org/mv#shot_02> .
<https://example.org/mv#shot_01> <https://example.org/mv#startSecond> "0.0"^^<http://www.w3.org/2001/XMLSchema#decimal> .
<https://example.org/mv#e2e_project_01> <https://example.org/mv#hasTimeline> <https://example.org/mv#timeline_main> .
<https://example.org/mv#audio_main> <https://example.org/mv#genre> "City Pop" .
<https://example.org/mv#image_02> <https://example.org/mv#height> "1080"^^<http://www.w3.org/2001/XMLSchema#integer> .
<https://example.org/mv#image_01> <https://example.org/mv#height> "1080"^^<http://www.w3.org/2001/XMLSchema#integer> .
<https://example.org/mv#timeline_main> <http://www.w3.org/2000/01/rdf-schema#label> "메인 타임라인"@ko .
<https://example.org/mv#shot_02> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#Shot> .
<https://example.org/mv#task_render> <https://example.org/mv#status> "completed" .
<https://example.org/mv#e2e_project_01> <http://www.w3.org/2000/01/rdf-schema#label> "시티팝 야경 60초 풀패키지 뮤직비디오"@ko .
<https://example.org/mv#agent_music> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#AIAgent> .
<https://example.org/mv#shot_01> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#Shot> .
<https://example.org/mv#task_lyric_gen> <http://www.w3.org/ns/prov#wasAssociatedWith> <https://example.org/mv#agent_lyricist> .
<https://example.org/mv#task_lyric_gen> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#LyricGenerationTask> .
<https://example.org/mv#e2e_project_01> <https://example.org/mv#hasAudio> <https://example.org/mv#audio_main> .
<https://example.org/mv#audio_main> <http://www.w3.org/ns/prov#wasGeneratedBy> <https://example.org/mv#task_audio_gen> .
<https://example.org/mv#video_main> <https://example.org/mv#durationSeconds> "60.0"^^<http://www.w3.org/2001/XMLSchema#decimal> .
<https://example.org/mv#shot_01> <https://example.org/mv#endSecond> "30.0"^^<http://www.w3.org/2001/XMLSchema#decimal> .
<https://example.org/mv#task_audio_gen> <https://example.org/mv#status> "completed" .
<https://example.org/mv#video_main> <http://www.w3.org/2000/01/rdf-schema#label> "최종 렌더링 뮤직비디오"@ko .
<https://example.org/mv#image_02> <https://example.org/mv#width> "1920"^^<http://www.w3.org/2001/XMLSchema#integer> .
<https://example.org/mv#task_audio_gen> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#AudioGenerationTask> .
<https://example.org/mv#agent_editor> <http://www.w3.org/2000/01/rdf-schema#label> "영상 편집 에이전트"@ko .
<https://example.org/mv#task_render> <http://www.w3.org/ns/prov#wasAssociatedWith> <https://example.org/mv#agent_editor> .
<https://example.org/mv#timeline_main> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#Timeline> .
<https://example.org/mv#task_subtitle_gen> <https://example.org/mv#dependsOn> <https://example.org/mv#timeline_main> .
<https://example.org/mv#agent_lyricist> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#AIAgent> .
<https://example.org/mv#e2e_project_01_brief> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#CreativeBrief> .
<https://example.org/mv#video_main> <https://example.org/mv#usesAudio> <https://example.org/mv#audio_main> .
<https://example.org/mv#agent_translator> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#AIAgent> .
<https://example.org/mv#shot_01> <http://www.w3.org/2000/01/rdf-schema#label> "첫 번째 밤거리 샷"@ko .
<https://example.org/mv#task_lyric_gen> <https://example.org/mv#status> "completed" .
<https://example.org/mv#e2e_project_01_brief> <https://example.org/mv#targetDurationSeconds> "60.0"^^<http://www.w3.org/2001/XMLSchema#decimal> .
<https://example.org/mv#agent_editor> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#AIAgent> .
<https://example.org/mv#shot_02> <https://example.org/mv#usesImage> <https://example.org/mv#image_02> .
<https://example.org/mv#shot_01> <https://example.org/mv#usesImage> <https://example.org/mv#image_01> .
<https://example.org/mv#video_main> <https://example.org/mv#hasTimeline> <https://example.org/mv#timeline_main> .
<https://example.org/mv#image_01> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#ImageAsset> .
<https://example.org/mv#task_render> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#RenderTask> .
<https://example.org/mv#audio_main> <https://example.org/mv#durationSeconds> "60.0"^^<http://www.w3.org/2001/XMLSchema#decimal> .
<https://example.org/mv#shot_02> <https://example.org/mv#startSecond> "30.0"^^<http://www.w3.org/2001/XMLSchema#decimal> .
<https://example.org/mv#task_audio_gen> <http://www.w3.org/2000/01/rdf-schema#label> "음원 트랙 자동 생성"@ko .
<https://example.org/mv#audio_main> <https://example.org/mv#bpm> "124"^^<http://www.w3.org/2001/XMLSchema#integer> .
<https://example.org/mv#agent_music> <http://www.w3.org/2000/01/rdf-schema#label> "음악 생성 AI 에이전트"@ko .
<https://example.org/mv#video_main> <https://example.org/mv#fileUri> <https://example.org/assets/citypop_final.mp4> .
<https://example.org/mv#image_02> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#ImageAsset> .
<https://example.org/mv#shot_02> <https://example.org/mv#endSecond> "60.0"^^<http://www.w3.org/2001/XMLSchema#decimal> .
<https://example.org/mv#shot_02> <https://example.org/mv#orderIndex> "2"^^<http://www.w3.org/2001/XMLSchema#integer> .
<https://example.org/mv#video_main> <http://www.w3.org/ns/prov#wasGeneratedBy> <https://example.org/mv#task_render> .
<https://example.org/mv#task_subtitle_gen> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#SubtitleGenerationTask> .
<https://example.org/mv#timeline_main> <https://example.org/mv#hasShot> <https://example.org/mv#shot_01> .
<https://example.org/mv#task_translation> <http://www.w3.org/ns/prov#wasAssociatedWith> <https://example.org/mv#agent_translator> .
<https://example.org/mv#e2e_project_01> <https://example.org/mv#hasImage> <https://example.org/mv#image_01> .
<https://example.org/mv#audio_main> <https://example.org/mv#lyricText> "Running through the city night under glowing neon signs" .
<https://example.org/mv#agent_subtitler> <http://www.w3.org/2000/01/rdf-schema#label> "자막 싱크 AI 에이전트"@ko .
<https://example.org/mv#agent_translator> <http://www.w3.org/2000/01/rdf-schema#label> "다국어 번역 AI 에이전트"@ko .
<https://example.org/mv#e2e_project_01> <https://example.org/mv#hasImage> <https://example.org/mv#image_02> .
<https://example.org/mv#shot_02> <http://www.w3.org/2000/01/rdf-schema#label> "두 번째 드라이브 샷"@ko .
<https://example.org/mv#image_01> <https://example.org/mv#width> "1920"^^<http://www.w3.org/2001/XMLSchema#integer> .
<https://example.org/mv#shot_01> <https://example.org/mv#orderIndex> "1"^^<http://www.w3.org/2001/XMLSchema#integer> .
<https://example.org/mv#image_02> <https://example.org/mv#fileUri> <https://example.org/assets/neon_drive.png> .
<https://example.org/mv#task_lyric_gen> <http://www.w3.org/2000/01/rdf-schema#label> "한국어 가사 작사 작업"@ko .
<https://example.org/mv#agent_subtitler> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#AIAgent> .
<https://example.org/mv#task_subtitle_gen> <http://www.w3.org/ns/prov#wasAssociatedWith> <https://example.org/mv#agent_subtitler> .
<https://example.org/mv#video_main> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://example.org/mv#MusicVideo> .
<https://example.org/mv#e2e_project_01> <https://example.org/mv#hasFinalVideo> <https://example.org/mv#video_main> .
<https://example.org/mv#image_01> <https://example.org/mv#fileUri> <https://example.org/assets/night_skyline.png> .
<https://example.org/mv#task_audio_gen> <http://www.w3.org/ns/prov#wasAssociatedWith> <https://example.org/mv#agent_music> .
<https://example.org/mv#task_translation> <http://www.w3.org/2000/01/rdf-schema#label> "영어 가사 번역 작업"@ko .
<https://example.org/mv#audio_main> <https://example.org/mv#fileUri> <https://example.org/assets/citypop_master.wav> .
<https://example.org/mv#agent_lyricist> <http://www.w3.org/2000/01/rdf-schema#label> "가사 작사 AI 에이전트"@ko .
<https://example.org/mv#audio_main> <http://www.w3.org/2000/01/rdf-schema#label> "메인 음원"@ko .
  }
}