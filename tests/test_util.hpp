#pragma once

#include <cmath>
#include <cstdio>

namespace dictest {

inline int& failures() {
  static int f = 0;
  return f;
}

}  // namespace dictest

#define CHECK(cond)                                                       \
  do {                                                                    \
    if (!(cond)) {                                                        \
      std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);        \
      ++dictest::failures();                                              \
    }                                                                     \
  } while (0)

#define CHECK_NEAR(a, b, tol)                                                  \
  do {                                                                         \
    const double _d = std::fabs(static_cast<double>(a) - static_cast<double>(b)); \
    if (_d > (tol)) {                                                          \
      std::printf("FAIL %s:%d: |%g - %g| = %g > %g\n", __FILE__, __LINE__,     \
                  static_cast<double>(a), static_cast<double>(b), _d,          \
                  static_cast<double>(tol));                                   \
      ++dictest::failures();                                                   \
    }                                                                          \
  } while (0)

#define TEST_REPORT()                                              \
  do {                                                             \
    if (dictest::failures()) {                                     \
      std::printf("%d check(s) failed\n", dictest::failures());    \
      return 1;                                                    \
    }                                                              \
    std::printf("all checks passed\n");                            \
    return 0;                                                      \
  } while (0)
