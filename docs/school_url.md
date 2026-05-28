이 파일에 적힌 모든 학교들의 학사일정을 크롤링하는 각 학교마다 로직을 만들고, DB에 저장한다.

이 파일에 포함되는 학교들은 점점 늘어날 것, 수정 빈번.

이때 학교마다의 크롤링 코드 혹은 url 경로 이름은 학교 domain을 따른다.
예: 가천대(gachon), 동서울대(dseoul), 서울대(snu), 고려대(korea) 등등

가천대: https://www.gachon.ac.kr/kor/1075/subview.do
동서울대: https://www.du.ac.kr/submenu.do?menuUrl=mk%2F8AIUzCNRzSS%2BQycenWQ%3D%3D&
서울대: https://www.snu.ac.kr/academics/resources/calendar
고려대(서울): https://registrar.korea.ac.kr/eduinfo/affairs/schedule.do
한체대: https://www.knsu.ac.kr/knsu/academic/academic-schedule.do?mode=list
한림대: https://www.hallym.ac.kr/hallym/1062/subview.do
