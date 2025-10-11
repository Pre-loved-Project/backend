from app.core.db import Base, engine

# 한번만 실행하는 스크립트
def reset_db():
    print("데이터베이스 초기화 중...")
    Base.metadata.drop_all(bind=engine, checkfirst=True)
    Base.metadata.create_all(bind=engine)
    print("초기화 완료!")

if __name__ == "__main__":
    reset_db()