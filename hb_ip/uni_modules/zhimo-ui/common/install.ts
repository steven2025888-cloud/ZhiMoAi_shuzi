import type { App } from 'vue';
import { mergeConfig } from './config';
import { ZHIMO_CONFIG_KEY, type ZhimoConfig } from './inject';

export default {
  install(app: App, userConfig?: ZhimoConfig) {
    const cfg = mergeConfig(userConfig);
    app.provide(ZHIMO_CONFIG_KEY, cfg);
  }
};
