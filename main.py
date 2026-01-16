import discord
import os
import datetime
from dotenv import load_dotenv
from openai import OpenAI

# 1. 설정 불러오기
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 2. OpenAI & Discord 연결
ai_client = OpenAI(api_key=OPENAI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'✅ {client.user} 봇이 준비되었습니다!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # 3. "!요약" 명령어 감지
    if message.content == '!요약':
        status_msg = await message.channel.send("⏳ 지난 12시간 동안의 대화를 수집하고 분석 중입니다...")

        try:
            # --- [Step 1] 12시간 전 시간 계산 ---
            now = datetime.datetime.now(datetime.timezone.utc)
            time_cutoff = now - datetime.timedelta(hours=12)

            # --- [Step 2] 대화 내용 긁어오기 ---
            chat_log = []
            
            async for msg in message.channel.history(after=time_cutoff, limit=None):
                if msg.author.bot: 
                    continue
                
                # 닉네임 가져오기
                name = msg.author.display_name
                
                # 🔥 [커스텀 매핑] "원래닉네임": "바꿀이름" 짝지어주기
                # 여기에 친구들 별명을 계속 추가하면 됩니다.
                nickname_map = {
                    "###": "머구리",
                    "-": "곽동호",
                    # 예시: "User123": "철수" 
                }

                # 1. 내 명단에 있는 놈이면? -> 내가 정한 이름으로 강제 개명!
                if name in nickname_map:
                    name = nickname_map[name]
                
                # 2. 명단엔 없는데, 여전히 이상한 닉네임(. , ?)이면? -> 본명 박제
                elif name in [".", "?", "??", "!"] or name.strip() == "":
                    name = f"{msg.author.name}"

                # 내용이 너무 긴 메시지 자르기
                content = msg.content
                if len(content) > 300:
                    content = content[:300] + "..."
                
                # 결과 리스트에 추가
                chat_log.append(f"{name}: {content}")

            if len(chat_log) < 3:
                await status_msg.edit(content="❌ 지난 12시간 동안 대화가 너무 적어서 요약할 게 없어요!")
                return

            full_text = "\n".join(chat_log)

            # [중요 안전장치] 12시간이라도 말이 너무 많으면 AI가 뻗으니까, 최신 10000자만 남김
            if len(full_text) > 10000:
                full_text = full_text[-10000:]
            
            guild_name = message.guild.name if message.guild else "이 채널"

            # --- [Step 3] AI에게 요약 시키기 ---
            prompt = f"""
            아래는 '{guild_name}' 디스코드 채널의 지난 12시간 대화 로그야.
            이 내용을 바탕으로 다음 **핵심 지침**을 엄격히 준수하여 요약해줘.

            🚨 **핵심 지침 (매우 중요)**:
            1. **모든 주제에 대해 구체적으로 서술할 것 (뭉뚱그리기 금지)**:
               - (게임) '게임 이야기를 함' (X) -> '롤 랭크 연패 후 정글러 탓을 하며 화냄' (O)
               - (음식) '저녁 메뉴 추천함' (X) -> '강남역 근처 마라탕 맛집 링크를 공유함' (O)
               - (개발) '코딩 질문이 오감' (X) -> '파이썬 들여쓰기 에러 때문에 실행이 안 돼서 멘붕 옴' (O)
               - (일상) '학교 가기 싫어함' (X) -> '내일 1교시 수업이라 일어나기 힘들다고 징징댐' (O)
               말투는 20대 커뮤니티 중독자 말투야. 직설적이고 저급해야해. 천박한 개드립도 섞어.
            
            2. **고유명사(키워드) 100% 유지**:
               - 대화에 나온 구체적인 이름(롤, 발로란트, 맥도날드, C++, 부산 등)을 절대 빼먹지 말고 그대로 요약에 넣을 것.

            ---
            
            1. **전체 요약**: 
               - 형식: "지난 12시간 동안 '{guild_name}'에서는 [핵심 키워드들]에 대한 이야기가 뜨거웠다."
               - 대화가 흘러간 순서대로 어떤 구체적인 이슈들이 있었는지 육하원칙에 맞춰 서술해줘.

            2. **참여자별 요약**:
               - 형식: "닉네임: [구체적인 발언 내용]"
               - 닉네임은 변경하지 말고 로그에 있는 그대로 적어줘.
               - 그 사람이 '무엇(What)'에 대해 '어떤 구체적인 반응(How)'을 보였는지 한 줄로 요약해줘. (단순히 '동의함', '반대함' 금지)

            [대화 로그]
            {full_text}
            """

            response = ai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "너는 대화 내용을 명확하게 요약해주는 서기야."},
                    {"role": "user", "content": prompt}
                ]
            )

            summary = response.choices[0].message.content
            
            # 결과 출력
            await status_msg.edit(content=f"📊 **지난 12시간 대화 요약**\n\n{summary}")
            print("✅ 요약 완료 및 전송")

        except Exception as e:
            await status_msg.edit(content=f"❌ 에러가 발생했습니다: {e}")
            print(f"에러 로그: {e}")

# 봇 실행
client.run(DISCORD_TOKEN)