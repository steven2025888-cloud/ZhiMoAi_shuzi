import type { ZhimoConfig } from './inject';

export const defaultConfig: ZhimoConfig = {
  defaultSize: 'md',
  defaultRound: true,
  zIndexBase: 2000
};

export function mergeConfig(user?: ZhimoConfig | null): ZhimoConfig {
  if (user != null) {
    return {
      defaultSize: user.defaultSize ?? defaultConfig.defaultSize,
      defaultRound: user.defaultRound ?? defaultConfig.defaultRound,
      zIndexBase: user.zIndexBase ?? defaultConfig.zIndexBase
    };
  }
  return defaultConfig;
}
