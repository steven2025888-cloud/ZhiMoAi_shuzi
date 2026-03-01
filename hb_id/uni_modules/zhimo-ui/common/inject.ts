export const ZHIMO_CONFIG_KEY = Symbol('ZHIMO_CONFIG_KEY');

export type ZhimoConfig = {
  defaultSize?: 'sm' | 'md' | 'lg';
  defaultRound?: boolean;
  zIndexBase?: number;
};
