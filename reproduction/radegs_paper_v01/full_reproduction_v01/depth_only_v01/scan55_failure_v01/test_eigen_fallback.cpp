// CPU-only TDD: captured RED, scaled/repeated-eigenvalue stress, and exact
// preservation of all successful float results. No tolerance changes per run.
#include <iostream>
#include <fstream>
#include <cmath>
#include <random>
#include <cstring>
#include "paper_geometry_precision.cuh"
int main(int argc,char** argv){
 if(argc!=2)return 2;
 std::ifstream f(argv[1]);glm::mat3 captured;
 for(int r=0;r<3;r++)for(int c=0;c<3;c++)f>>captured[c][r];if(!f)return 3;
 std::mt19937 gen(550024);std::uniform_real_distribution<float> uni(-1,1);
 unsigned bad=0,fallback=0,kept=0;double maxrel=0;
 for(int i=0;i<10001;i++){
  glm::mat3 A=captured;
  if(i){
   glm::vec3 v(uni(gen),uni(gen),uni(gen));v=glm::normalize(v);
   float unit=std::pow(10.f,float((i%17)-12)),gap=(i%4==0?0.f:std::pow(10.f,-float(i%7)));
   A=unit*(glm::mat3(1.f)+gap*glm::outerProduct(v,v));
  }
  float scale=0;for(int c=0;c<3;c++)for(int r=0;r<3;r++)scale=glm::max(scale,glm::abs(A[c][r]));
  glm::vec3 olde(0),e(0);glm::mat3 oldU(0),U(0);
  auto oldn=glm::findEigenvaluesSymReal(A/scale,olde,oldU);olde*=scale;
  auto n=paper_find_eigenvalues(A,e,U);
  bool good=n==3;
  auto rec=U*glm::mat3(e.x,0,0,0,e.y,0,0,0,e.z)*glm::transpose(U);
  double rel=0;
  for(int c=0;c<3;c++)for(int r=0;r<3;r++){
   double err=std::abs(double(rec[c][r]-A[c][r]))/scale;
   good=good&&std::isfinite(err);if(std::isfinite(err))rel=std::max(rel,err);
  }
  maxrel=std::max(maxrel,rel);good=good&&rel<1e-5&&e.x>0&&e.y>0&&e.z>0;
  if(oldn==3){kept++;good=good&&std::memcmp(&olde,&e,sizeof(e))==0&&std::memcmp(&oldU,&U,sizeof(U))==0;}else fallback++;
  if(!good){bad++;if(bad<6)std::cout<<"FAIL fixture "<<i<<" old_count "<<oldn<<" count "<<n<<" rel "<<rel<<"\n";}
 }
 std::cout<<"fixtures 10001 unchanged_float "<<kept<<" fallback_required "<<fallback<<" failures "<<bad<<" max_relative_reconstruction "<<maxrel<<"\n";
 return bad?1:0;
}
