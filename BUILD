load("//util/shell/gbash:gbash.bzl", "sh_binary_sar")
load("//storage/binfs:binfs.bzl", "gensignature")

sh_binary_sar(
  name = "deal_reviewer",
  srcs = ["deal_reviewer.sh"],
  data = ["bot.bgl.json"],
  deps = ["//util/shell/gbash"],
)

gensignature(
  name = "deal_reviewer_sig",
  srcs = [":deal_reviewer"],
)
