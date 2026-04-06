PS C:\Users\ilya1\Documents\rd_projects\ai-engineering-course\lesson-02-data-engineering\dvc-homework> python evaluate.py
==================================================
CHECK 1: Repo + DVC init
==================================================
  [PASS] git repo exists (+3)
  [PASS] .dvc/ exists (+3)
  [PASS] .dvcignore exists (+2)
  [PASS] dvc works (+2)

==================================================
CHECK 2: DVC tracking
==================================================
  [PASS] dataset.csv.dvc exists (+4)
  [PASS] .dvc has md5 hash (+3)
  [PASS] .dvc tracks dataset.csv (+2)
  [PASS] dataset.csv in .gitignore (+3)

==================================================
CHECK 3: Commits (v1 + v2)
==================================================
  [PASS] At least 3 commits (+3)
  [PASS] Commit with 'v1' (+3)
  [PASS] Commit with 'v2' (+3)

==================================================
CHECK 4: Data quality (v2)
==================================================
  [PASS] Has header (+1)
  [PASS] 10 data rows (+4)
  [PASS] No duplicate ids (+4)
  [PASS] No empty values (+4)
  [PASS] All categories lowercase (+3)
  [PASS] Bob = enterprise (+3)
  [PASS] Hank value = 4800 (+3)

==================================================
CHECK 5: DVC cache
==================================================
  [PASS] Cache has files (+3)
  [PASS] 2+ versions cached (+4)

==================================================
CHECK 6: Final state
==================================================
  [PASS] dvc status clean (+4)

==================================================
РЕЗУЛЬТАТ: 64/64 балів (100%)
==================================================
Відмінно!